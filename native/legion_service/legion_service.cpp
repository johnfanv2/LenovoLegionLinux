#include <fcntl.h>
#include <glob.h>
#include <grp.h>
#include <linux/fs.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>
#include <yaml-cpp/yaml.h>

namespace fs = std::filesystem;
using Json = nlohmann::json;

namespace {
constexpr std::string_view kDefaultSocket = "/run/legion-linux/control.sock";
constexpr std::string_view kAccessGroup = "legion-linux";
constexpr std::size_t kReadChunkSize = 64U * 1024U;
constexpr std::size_t kMaxFanCurve = 256U * 1024U;
constexpr std::size_t kMaxImage = 1024U * 1024U;
constexpr int kTimeoutSeconds = 10;

class ServiceError : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

class UniqueFd {
 public:
  explicit UniqueFd(int fd = -1) noexcept : fd_(fd) {}
  ~UniqueFd() { reset(); }
  UniqueFd(const UniqueFd&) = delete;
  UniqueFd& operator=(const UniqueFd&) = delete;
  UniqueFd(UniqueFd&& other) noexcept : fd_(other.release()) {}
  UniqueFd& operator=(UniqueFd&& other) noexcept {
    if (this != &other) reset(other.release());
    return *this;
  }
  [[nodiscard]] int get() const noexcept { return fd_; }
  [[nodiscard]] int release() noexcept { return std::exchange(fd_, -1); }
  void reset(int fd = -1) noexcept {
    if (fd_ >= 0) ::close(fd_);
    fd_ = fd;
  }
  explicit operator bool() const noexcept { return fd_ >= 0; }

 private:
  int fd_;
};

void write_all(int fd, std::string_view data) {
  std::size_t offset = 0;
  while (offset < data.size()) {
    const auto count = ::send(fd, data.data() + offset, data.size() - offset,
                              MSG_NOSIGNAL);
    if (count < 0) {
      if (errno == EINTR) continue;
      throw ServiceError("could not write message");
    }
    offset += static_cast<std::size_t>(count);
  }
}

Json receive_message(int fd) {
  std::string payload;
  payload.reserve(kReadChunkSize);
  for (;;) {
    if (!payload.empty()) {
      Json value = Json::parse(payload, nullptr, false);
      if (!value.is_discarded()) {
        if (!value.is_object())
          throw ServiceError("JSON message must be an object");
        return value;
      }
    }

    std::array<char, kReadChunkSize> chunk{};
    const auto count = ::recv(fd, chunk.data(), chunk.size(), 0);
    if (count == 0) {
      if (payload.empty()) throw ServiceError("empty message");
      throw ServiceError("incomplete or invalid JSON message");
    }
    if (count < 0) {
      if (errno == EINTR) continue;
      throw ServiceError("could not read message");
    }
    payload.append(chunk.data(), static_cast<std::size_t>(count));
  }
}

void send_message(int fd, const Json& value) {
  const std::string payload = value.dump();
  write_all(fd, payload);
}

std::optional<fs::path> first_match(const std::vector<std::string>& patterns) {
  for (const auto& pattern : patterns) {
    glob_t matches{};
    const int result = ::glob(pattern.c_str(), GLOB_NOSORT, nullptr, &matches);
    if (result == 0 && matches.gl_pathc > 0) {
      const fs::path match(matches.gl_pathv[0]);
      ::globfree(&matches);
      return match;
    }
    ::globfree(&matches);
  }
  return std::nullopt;
}

std::string read_text(const fs::path& path) {
  std::ifstream input(path);
  if (!input) throw ServiceError("cannot read hardware attribute");
  std::string value((std::istreambuf_iterator<char>(input)), {});
  while (!value.empty() && (value.back() == '\n' || value.back() == '\r'))
    value.pop_back();
  return value;
}

void write_text(const fs::path& path, std::string_view value) {
  std::ofstream output(path);
  if (!output) throw ServiceError("cannot write hardware attribute");
  output << value;
  if (!output) throw ServiceError("hardware write failed");
}

enum class Kind { Boolean, Integer, Number, String, Charging };
struct FeatureDef {
  bool writable;
  Kind kind;
  std::vector<std::string> paths;
  std::optional<long long> minimum;
  std::optional<long long> maximum;
};

std::string legion_base() {
  if (fs::exists("/sys/module/legion_laptop/drivers/platform:legion/legion"))
    return "/sys/module/legion_laptop/drivers/platform:legion/legion";
  return "/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00";
}

std::map<std::string, FeatureDef> feature_definitions() {
  const std::string l = legion_base();
  const std::string i = "/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00";
  auto rw_bool = [](std::vector<std::string> paths) {
    return FeatureDef{true, Kind::Boolean, std::move(paths), {}, {}};
  };
  auto rw_int = [](std::string path, long long low, long long high) {
    return FeatureDef{true, Kind::Integer, {std::move(path)}, low, high};
  };
  return {
      {"LockFanController", rw_bool({l + "/lockfancontroller"})},
      {"BatteryConservation", rw_bool({i + "/conservation_mode"})},
      {"RapidChargingFeature", rw_bool({l + "/rapidcharge"})},
      {"FnLockFeature", rw_bool({i + "/fn_lock"})},
      {"WinkeyFeature", rw_bool({l + "/winkey"})},
      {"TouchpadFeature", rw_bool({i + "/touchpad", l + "/touchpad"})},
      {"CameraPowerFeature", {false, Kind::Boolean, {i + "/camera_power"}, {}, {}}},
      {"OverdriveFeature", rw_bool({l + "/overdrive"})},
      {"GsyncFeature", rw_bool({l + "/gsync"})},
      {"AlwaysOnUSBChargingFeature", rw_bool({i + "/usb_charging"})},
      {"MaximumFanSpeedFeature", rw_bool({l + "/fan_fullspeed"})},
      {"PlatformProfileFeature", {true, Kind::String,
        {"/sys/class/platform-profile/platform-profile-*/profile",
         l + "/platform-profile/platform-profile-*/profile"}, {}, {}}},
      {"IsOnPowerSupplyFeature", {false, Kind::Boolean,
        {"/sys/class/power_supply/ADP0/online"}, {}, {}}},
      {"BatteryIsCharging", {false, Kind::Charging,
        {"/sys/class/power_supply/BAT0/status"}, {}, {}}},
      {"BatteryCurrentCapacityPercentage", {false, Kind::Number,
        {"/sys/class/power_supply/BAT0/capacity"}, {}, {}}},
      {"CPUOverclock", rw_bool({l + "/cpu_oc"})},
      {"GPUOverclock", rw_bool({l + "/gpu_oc"})},
      {"CPUShorttermPowerLimit", rw_int(l + "/cpu_shortterm_powerlimit", 5, 200)},
      {"CPULongtermPowerLimit", rw_int(l + "/cpu_longterm_powerlimit", 5, 200)},
      {"CPUPeakPowerLimit", rw_int(l + "/cpu_peak_powerlimit", 0, 200)},
      {"CPUAPUSPPTPowerLimit", rw_int(l + "/cpu_apu_sppt_powerlimit", 0, 100)},
      {"CPUDefaultPowerLimit", rw_int(l + "/cpu_default_powerlimit", 0, 100)},
      {"CPUCrossLoadingPowerLimit", rw_int(l + "/cpu_cross_loading_powerlimit", 0, 100)},
      {"GPUBoostClock", rw_int(l + "/gpu_boost_clock", 0, 10000)},
      {"GPUCTGPPowerLimit", rw_int(l + "/gpu_ctgp_powerlimit", 0, 200)},
      {"GPUPPABPowerLimit", rw_int(l + "/gpu_ppab_powerlimit", 0, 200)},
      {"GPUTemperatureLimit", rw_int(l + "/gpu_temperature_limit", 0, 120)},
      {"YLogoLight", rw_bool({"/sys/class/leds/platform::ylogo/brightness"})},
      {"IOPortLight", rw_bool({"/sys/class/leds/platform::ioport/brightness"})},
      {"NVIDIAGPUIsRunning", {false, Kind::Boolean,
        {"/sys/bus/pci/devices/0000:01:00.0/power/runtime_status"}, {}, {}}},
  };
}

Json typed_value(const FeatureDef& definition, const fs::path& path) {
  const std::string value = read_text(path);
  switch (definition.kind) {
    case Kind::Boolean:
      if (path.filename() == "runtime_status") return value != "suspended";
      return value != "0";
    case Kind::Integer: return std::stoll(value);
    case Kind::Number: return std::stod(value);
    case Kind::Charging: return value == "Charging";
    case Kind::String: return value;
  }
  throw ServiceError("invalid feature type");
}

std::string value_for_write(const FeatureDef& definition, const Json& value) {
  if (definition.kind == Kind::Boolean) {
    if (value.is_boolean()) return value.get<bool>() ? "1" : "0";
    if (value.is_number_integer()) return value.get<long long>() != 0 ? "1" : "0";
    if (value.is_string()) {
      const std::string text = value.get<std::string>();
      if (text == "1" || text == "true" || text == "True") return "1";
      if (text == "0" || text == "false" || text == "False") return "0";
    }
    throw ServiceError("invalid boolean feature value");
  }
  if (definition.kind == Kind::Integer) {
    const long long integer = value.is_string() ? std::stoll(value.get<std::string>())
                                                : value.get<long long>();
    if ((definition.minimum && integer < *definition.minimum) ||
        (definition.maximum && integer > *definition.maximum))
      throw ServiceError("feature value is outside allowed range");
    return std::to_string(integer);
  }
  if (definition.kind == Kind::String) return value.get<std::string>();
  throw ServiceError("feature is read-only");
}

class Service {
 public:
  Service() : features_(feature_definitions()) {}

  Json dispatch(const Json& request) {
    if (request.value("version", 0) != 1) throw ServiceError("unsupported protocol version");
    const std::string operation = request.value("operation", "");
    const Json arguments = request.value("arguments", Json::object());
    if (!arguments.is_object()) throw ServiceError("invalid arguments");
    if (operation.starts_with("feature."))
      return feature(operation.substr(8), arguments);
    if (operation.starts_with("fan.")) return fan(operation.substr(4), arguments);
    if (operation == "boot.status") return Json::array({false, 0, 0});
    if (operation == "boot.enable" || operation == "boot.restore")
      throw ServiceError("boot logo operation is not available in the native service yet");
    throw ServiceError("operation is not allowed");
  }

 private:
  Json feature(const std::string& method, const Json& arguments) {
    const std::string name = arguments.value("name", "");
    const auto found = features_.find(name);
    if (found == features_.end()) throw ServiceError("feature is not allowed");
    const FeatureDef& definition = found->second;
    const auto path = first_match(definition.paths);
    if (method == "exists") return path.has_value();
    if (!path) throw ServiceError("feature " + name + " is not available on this system");
    if (method == "get") return typed_value(definition, *path);
    if (method == "values") {
      Json values = Json::array();
      if (name == "PlatformProfileFeature") {
        std::vector<std::string> choice_paths;
        for (const auto& item : definition.paths) {
          choice_paths.push_back(fs::path(item).parent_path().string() + "/choices");
        }
        if (const auto choices = first_match(choice_paths)) {
          static const std::map<std::string, std::string> labels{{"low-power", "Low Power"},
            {"balanced", "Balanced Mode"}, {"performance", "Performance Mode"},
            {"custom", "Custom Mode"}, {"max-power", "Max Power"}};
          std::string token;
          std::istringstream input(read_text(*choices));
          while (input >> token) {
            const auto label = labels.find(token);
            values.push_back({{"value", token},
                              {"name", label == labels.end() ? token : label->second}});
          }
        }
      }
      return values;
    }
    if (method == "set") {
      if (!definition.writable) throw ServiceError("feature operation is not allowed");
      const std::string output = value_for_write(definition, arguments.at("value"));
      if (name == "PlatformProfileFeature") {
        const auto choices = first_match({path->parent_path().string() + "/choices"});
        if (!choices || (" " + read_text(*choices) + " ").find(" " + output + " ") == std::string::npos)
          throw ServiceError("invalid platform profile");
      }
      write_text(*path, output);
      return nullptr;
    }
    throw ServiceError("feature operation is not allowed");
  }

  Json fan(const std::string& method, const Json& arguments) {
    const auto hwmon = first_match({legion_base() + "/hwmon/hwmon*"});
    if (method == "exists") return hwmon.has_value();
    if (!hwmon) throw ServiceError("fan control is not available on this system");
    auto has = [&](std::string_view name) { return fs::exists(*hwmon / name); };
    if (method == "has_minifancurve") return has("minifancurve");
    if (method == "has_fan_2_speed") return has("pwm2_auto_point1_pwm");
    if (method == "has_temperature_curve") return has("pwm1_auto_point1_temp");
    if (method == "has_acceleration_curve") return has("pwm1_auto_point1_accel");
    if (method == "get_minifancuve") return read_text(*hwmon / "minifancurve") != "0";
    if (method == "set_minifancuve") {
      write_text(*hwmon / "minifancurve", arguments.value("value", false) ? "1" : "0");
      return nullptr;
    }
    auto point = [&](std::string_view pattern, int id) {
      std::string name(pattern);
      name.replace(name.find("{}"), 2, std::to_string(id));
      return *hwmon / name;
    };
    auto read_integer = [&](const fs::path& path) {
      return std::stoll(read_text(path));
    };
    auto read_optional = [&](const fs::path& path) {
      return fs::exists(path) ? read_integer(path) : 0LL;
    };
    const bool fan2 = has("pwm2_auto_point1_pwm");
    const bool temperatures = has("pwm1_auto_point1_temp_hyst") &&
        has("pwm1_auto_point1_temp") && has("pwm2_auto_point1_temp_hyst") &&
        has("pwm2_auto_point1_temp") && has("pwm3_auto_point1_temp_hyst") &&
        has("pwm3_auto_point1_temp");
    const bool acceleration = has("pwm1_auto_point1_accel") &&
        has("pwm1_auto_point1_decel");
    if (method == "read") {
      const long long fan1_max = read_integer(*hwmon / "fan1_max");
      const long long fan2_max = fan2 ? read_integer(*hwmon / "fan2_max") : fan1_max;
      YAML::Node curve;
      curve["name"] = "unknown";
      YAML::Node entries(YAML::NodeType::Sequence);
      for (int id = 1; id <= 10; ++id) {
        const long long pwm1 = read_integer(point("pwm1_auto_point{}_pwm", id));
        const long long pwm2 = fan2 ? read_integer(point("pwm2_auto_point{}_pwm", id)) : pwm1;
        YAML::Node entry;
        entry["fan1_speed"] =
            ((pwm1 * fan1_max + 25500 - 1) / 25500) * 100;
        entry["fan2_speed"] =
            ((pwm2 * fan2_max + 25500 - 1) / 25500) * 100;
        entry["cpu_lower_temp"] = temperatures ? read_optional(point("pwm1_auto_point{}_temp_hyst", id)) : 0;
        entry["cpu_upper_temp"] = temperatures ? read_optional(point("pwm1_auto_point{}_temp", id)) : 0;
        entry["gpu_lower_temp"] = temperatures ? read_optional(point("pwm2_auto_point{}_temp_hyst", id)) : 0;
        entry["gpu_upper_temp"] = temperatures ? read_optional(point("pwm2_auto_point{}_temp", id)) : 0;
        entry["ic_lower_temp"] = temperatures ? read_optional(point("pwm3_auto_point{}_temp_hyst", id)) : 0;
        entry["ic_upper_temp"] = temperatures ? read_optional(point("pwm3_auto_point{}_temp", id)) : 0;
        entry["acceleration"] = acceleration ? read_optional(point("pwm1_auto_point{}_accel", id)) : 0;
        entry["deceleration"] = acceleration ? read_optional(point("pwm1_auto_point{}_decel", id)) : 0;
        entries.push_back(entry);
      }
      curve["entries"] = entries;
      curve["enable_minifancurve"] = has("minifancurve") &&
          read_text(*hwmon / "minifancurve") != "0";
      YAML::Emitter output;
      output << curve;
      return std::string(output.c_str());
    }
    if (method == "write") {
      const std::string text = arguments.value("yaml", "");
      if (text.empty() || text.size() > kMaxFanCurve)
        throw ServiceError("invalid fan curve");
      YAML::Node curve;
      try { curve = YAML::Load(text); }
      catch (const YAML::Exception&) { throw ServiceError("invalid fan curve"); }
      const YAML::Node entries = curve["entries"];
      if (!entries.IsSequence() || entries.size() == 0 || entries.size() > 10)
        throw ServiceError("invalid fan curve entries");
      const long long fan1_max = read_integer(*hwmon / "fan1_max");
      const long long fan2_max = fan2 ? read_integer(*hwmon / "fan2_max") : fan1_max;
      if (fan1_max <= 0 || fan2_max <= 0)
        throw ServiceError("invalid maximum fan speed");
      auto number = [](const YAML::Node& node, std::string_view field) {
        try {
          const double value = node.as<double>();
          if (!std::isfinite(value)) throw ServiceError("invalid fan curve value");
          return value;
        } catch (const YAML::Exception&) {
          throw ServiceError("invalid fan curve field: " + std::string(field));
        }
      };
      auto integer = [&](const YAML::Node& node, std::string_view field) {
        const double value = number(node, field);
        if (value < static_cast<double>(std::numeric_limits<long long>::min()) ||
            value > static_cast<double>(std::numeric_limits<long long>::max()) ||
            std::trunc(value) != value)
          throw ServiceError("invalid fan curve field: " + std::string(field));
        return static_cast<long long>(value);
      };
      struct ValidatedEntry {
        double speed1;
        double speed2;
        long long cpu_lower;
        long long cpu_upper;
        long long gpu_lower;
        long long gpu_upper;
        long long ic_lower;
        long long ic_upper;
        long long accel;
        long long decel;
      };
      std::vector<ValidatedEntry> validated;
      validated.reserve(entries.size());
      for (const YAML::Node& entry : entries) {
        ValidatedEntry value{
            number(entry["fan1_speed"], "fan1_speed"),
            number(entry["fan2_speed"], "fan2_speed"),
            integer(entry["cpu_lower_temp"], "cpu_lower_temp"),
            integer(entry["cpu_upper_temp"], "cpu_upper_temp"),
            integer(entry["gpu_lower_temp"], "gpu_lower_temp"),
            integer(entry["gpu_upper_temp"], "gpu_upper_temp"),
            integer(entry["ic_lower_temp"], "ic_lower_temp"),
            integer(entry["ic_upper_temp"], "ic_upper_temp"),
            integer(entry["acceleration"], "acceleration"),
            integer(entry["deceleration"], "deceleration")};
        if (value.speed1 < 0 || value.speed2 < 0)
          throw ServiceError("invalid fan speed");
        validated.push_back(value);
      }
      std::optional<bool> minifancurve;
      if (has("minifancurve") && curve["enable_minifancurve"]) {
        try { minifancurve = curve["enable_minifancurve"].as<bool>(); }
        catch (const YAML::Exception&) {
          throw ServiceError("invalid enable_minifancurve value");
        }
      }
      if (minifancurve)
        write_text(*hwmon / "minifancurve", *minifancurve ? "1" : "0");
      auto write_if_present = [&](const fs::path& path, long long value) {
        if (fs::exists(path)) write_text(path, std::to_string(value));
      };
      for (std::size_t index = 0; index < validated.size(); ++index) {
        const ValidatedEntry& entry = validated[index];
        const int id = static_cast<int>(index + 1);
        write_text(point("pwm1_auto_point{}_pwm", id),
                   std::to_string(static_cast<long long>(
                       std::floor(entry.speed1 / 100.0) * 25500.0 /
                       static_cast<double>(fan1_max))));
        if (fan2) write_text(point("pwm2_auto_point{}_pwm", id),
                            std::to_string(static_cast<long long>(
                                std::floor(entry.speed2 / 100.0) * 25500.0 /
                                static_cast<double>(fan2_max))));
        if (temperatures) {
          write_if_present(point("pwm1_auto_point{}_temp_hyst", id), entry.cpu_lower);
          write_if_present(point("pwm1_auto_point{}_temp", id), entry.cpu_upper);
          write_if_present(point("pwm2_auto_point{}_temp_hyst", id), entry.gpu_lower);
          write_if_present(point("pwm2_auto_point{}_temp", id), entry.gpu_upper);
          write_if_present(point("pwm3_auto_point{}_temp_hyst", id), entry.ic_lower);
          write_if_present(point("pwm3_auto_point{}_temp", id), entry.ic_upper);
        }
        if (acceleration) {
          write_if_present(point("pwm1_auto_point{}_accel", id), entry.accel);
          write_if_present(point("pwm1_auto_point{}_decel", id), entry.decel);
        }
      }
      return nullptr;
    }
    throw ServiceError("fan operation is not allowed");
  }

  std::map<std::string, FeatureDef> features_;
};

bool peer_allowed(int fd) {
  ucred credentials{};
  socklen_t length = sizeof(credentials);
  if (::getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &credentials, &length) != 0) return false;
  if (credentials.uid == 0) return true;

  const group* access_group = ::getgrnam(kAccessGroup.data());
  if (access_group == nullptr) return false;
  if (credentials.gid == access_group->gr_gid) return true;

  std::ifstream groups("/proc/" + std::to_string(credentials.pid) + "/status");
  std::string line;
  while (std::getline(groups, line)) {
    if (!line.starts_with("Groups:")) continue;
    std::istringstream values(line.substr(7));
    unsigned long long gid = 0;
    while (values >> gid) {
      if (gid == static_cast<unsigned long long>(access_group->gr_gid)) return true;
    }
    break;
  }
  return false;
}

void set_timeout(int fd) {
  const timeval timeout{kTimeoutSeconds, 0};
  ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
  ::setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
}

void serve(std::string_view socket_path) {
  const fs::path path(socket_path);
  fs::create_directories(path.parent_path());
  fs::remove(path);
  const group* access_group = ::getgrnam(kAccessGroup.data());
  if (access_group == nullptr) throw ServiceError("legion-linux group does not exist");
  if (::chown(path.parent_path().c_str(), 0, access_group->gr_gid) != 0 ||
      ::chmod(path.parent_path().c_str(), 0750) != 0)
    throw ServiceError("cannot secure Unix socket directory");
  UniqueFd listener(::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0));
  if (!listener) throw ServiceError("cannot create Unix socket");
  sockaddr_un address{};
  address.sun_family = AF_UNIX;
  if (socket_path.size() >= sizeof(address.sun_path)) throw ServiceError("socket path is too long");
  std::copy(socket_path.begin(), socket_path.end(), address.sun_path);
  if (::bind(listener.get(), reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0)
    throw ServiceError("cannot bind Unix socket");
  if (::chown(path.c_str(), 0, access_group->gr_gid) != 0 ||
      ::chmod(path.c_str(), 0660) != 0)
    throw ServiceError("cannot secure Unix socket");
  if (::listen(listener.get(), 16) != 0) throw ServiceError("cannot listen on Unix socket");
  Service service;
  for (;;) {
    UniqueFd client(::accept4(listener.get(), nullptr, nullptr, SOCK_CLOEXEC));
    if (!client) {
      if (errno == EINTR) continue;
      throw ServiceError("cannot accept client");
    }
    set_timeout(client.get());
    try {
      if (!peer_allowed(client.get())) throw ServiceError("client is not an interactive user");
      send_message(client.get(), {{"ok", true}, {"result", service.dispatch(receive_message(client.get()))}});
    } catch (const std::exception& error) {
      try { send_message(client.get(), {{"ok", false}, {"error", error.what()}}); }
      catch (const std::exception&) {}
    }
  }
}
}  // namespace

int main(int argc, char** argv) {
  try {
    const std::string_view socket_path = argc == 3 && std::string_view(argv[1]) == "--socket"
                                           ? std::string_view(argv[2]) : kDefaultSocket;
    serve(socket_path);
  } catch (const std::exception& error) {
    std::cerr << "legion_service: " << error.what() << '\n';
    return 1;
  }
  return 0;
}
