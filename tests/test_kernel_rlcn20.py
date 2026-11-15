"""Exercise RLCN20 graphics safeguards without accessing firmware."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "kernel_module/legion-laptop.c"


def function(source, name):
    match = re.search(
        r"^static\s+[\w\s*]+\b" + name + r"\s*\([^;{}]*\)\s*\{", source, re.M
    )
    assert match is not None, name
    return source[match.start() : source.index("\n}", match.end()) + 2]


HARNESS = r"""
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>
#include <sys/types.h>
typedef unsigned char u8;
#define ERESTARTSYS 512
#define LEGION_WMI_GAMEZONE_GUID "guid"
#define WMI_METHOD_ID_GETGSYNCSTATUS 1
struct device { int dummy; };
struct device_attribute { int dummy; };
struct platform_device { struct device dev; };
struct legion_private { int fancurve_mutex; struct platform_device *platform_device; };
enum rlcn20_graphics_mode { RLCN20_UMA = 0, RLCN20_DISCRETE = 1, RLCN20_HYBRID = 4 };
static bool ec_readonly, allow_rlcn20_mux_write, supported = true;
static int read_err, get_err, set_err, set_calls, set_value, legacy_calls;
static u8 read_mode;
static struct platform_device platform;
static struct legion_private priv = { .platform_device = &platform };
#define mutex_lock(x) ((void)(x))
#define mutex_unlock(x) ((void)(x))
#define dev_notice(...) ((void)0)
static struct legion_private *dev_get_drvdata(struct device *dev) { (void)dev; return &priv; }
static bool rlcn20_mux_supported(struct legion_private *p) { (void)p; return supported; }
static int rlcn20_get_graphics_mode(u8 *mode) { *mode = read_mode; return read_err; }
static int rlcn20_wmi_get_gsync(unsigned long *state) { *state = 0; return get_err; }
static int rlcn20_wmi_set_gsync(int discrete) { set_calls++; set_value = discrete; return set_err; }
static int sysfs_streq(const char *a, const char *b) {
    size_t n = strlen(b); return !strncmp(a, b, n) && (a[n] == '\0' || (a[n] == '\n' && a[n+1] == '\0'));
}
static ssize_t show_simple_wmi_attribute(struct device *d, struct device_attribute *a, char *b,
                                         const char *g, int i, int method, bool invert, int n) {
    (void)d; (void)a; (void)b; (void)g; (void)i; (void)method; (void)invert; (void)n;
    legacy_calls++; return 2;
}
__FUNCTIONS__
int main(void) {
    struct device d = {0}; struct device_attribute a = {0}; char buf[8];
    assert(graphics_mode_store(&d, &a, "hybrid\n", 7) == -EPERM);
    allow_rlcn20_mux_write = true; ec_readonly = true;
    assert(graphics_mode_store(&d, &a, "discrete", 8) == -EPERM);
    ec_readonly = false;
    assert(graphics_mode_store(&d, &a, "integrated", 10) == -EOPNOTSUPP);
    assert(graphics_mode_store(&d, &a, "bad", 3) == -EINVAL);
    supported = false; assert(graphics_mode_store(&d, &a, "hybrid", 6) == -EOPNOTSUPP);
    supported = true; get_err = -EIO;
    assert(graphics_mode_store(&d, &a, "hybrid", 6) == -EIO && set_calls == 0);
    get_err = 0; set_err = -EIO;
    assert(graphics_mode_store(&d, &a, "hybrid", 6) == -EIO && set_value == 0);
    set_err = 0; assert(graphics_mode_store(&d, &a, "discrete", 8) == 8 && set_value == 1);
    assert(graphics_mode_store(&d, &a, "discrete", 8) == 8 && set_calls == 3);
    read_err = 0; read_mode = RLCN20_UMA;
    assert(gsync_show(&d, &a, buf) == -EOPNOTSUPP && legacy_calls == 0);
    read_mode = RLCN20_HYBRID; assert(gsync_show(&d, &a, buf) == 2 && legacy_calls == 1);
    read_err = -EIO; assert(gsync_show(&d, &a, buf) == 2 && legacy_calls == 2);
    read_err = -EOPNOTSUPP; assert(gsync_show(&d, &a, buf) == 2 && legacy_calls == 3);
    read_err = -EINTR; assert(gsync_show(&d, &a, buf) == -EINTR && legacy_calls == 3);
    return 0;
}
"""

ALLOWED_BIOS = (
    "RLCN20WW", "RLCN21WW", "RLCN25WW", "RLCN26WW", "RLCN27WW",
    "RLCN29WW", "RLCN31WW", "RLCN32WW", "RLCN33WW", "RLCN34WW",
)

BIOS_HARNESS = r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#define DMI_BIOS_VERSION 1
#define DMI_PRODUCT_NAME 2
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
struct model_config { int unused; };
static const struct model_config model_rlcn = {0}, other_model = {0};
struct legion_private { const struct model_config *conf; };
static const char *current_bios, *current_product;
static const char *dmi_get_system_info(int id) {
    return id == DMI_BIOS_VERSION ? current_bios : NULL;
}
static bool dmi_match(int id, const char *expected) {
    return id == DMI_PRODUCT_NAME && current_product &&
           !strcmp(current_product, expected);
}
__TABLE__
__FUNCTION__
int main(void) {
    struct legion_private priv = { .conf = &model_rlcn };
    const char *allowed[] = {
        "RLCN20WW", "RLCN21WW", "RLCN25WW", "RLCN26WW", "RLCN27WW",
        "RLCN29WW", "RLCN31WW", "RLCN32WW", "RLCN33WW", "RLCN34WW",
    };
    const char *rejected[] = {
        "RLCN19WW", "RLCN22WW", "RLCN24WW", "RLCN28WW", "RLCN30WW",
        "RLCN35WW", "RLCN34WW-next", "RLCN34WW ", "ABCN34WW", "",
    };
    current_product = "83LT";
    for (size_t i = 0; i < ARRAY_SIZE(allowed); i++) {
        current_bios = allowed[i];
        assert(rlcn20_mux_supported(&priv));
    }
    for (size_t i = 0; i < ARRAY_SIZE(rejected); i++) {
        current_bios = rejected[i];
        assert(!rlcn20_mux_supported(&priv));
    }
    current_bios = NULL;
    assert(!rlcn20_mux_supported(&priv));
    current_bios = "RLCN29WW";
    current_product = "83LV";
    assert(!rlcn20_mux_supported(&priv));
    current_product = "83LT ";
    assert(!rlcn20_mux_supported(&priv));
    current_product = "83LT";
    priv.conf = &other_model;
    assert(!rlcn20_mux_supported(&priv));
    return 0;
}
"""


class Rlcn20Test(unittest.TestCase):
    def test_safeguards_and_legacy_fallback(self):
        source = SOURCE.read_text()
        names = ("rlcn20_request_graphics_mode", "graphics_mode_store", "gsync_show")
        code = HARNESS.replace(
            "__FUNCTIONS__", "\n\n".join(function(source, n) for n in names)
        )
        with tempfile.TemporaryDirectory() as tmp:
            src, binary = Path(tmp) / "test.c", Path(tmp) / "test"
            src.write_text(code)
            subprocess.run(
                ["gcc", "-std=gnu11", "-Wall", "-Werror", str(src), "-o", str(binary)],
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_scope_and_no_efi_writes(self):
        source = SOURCE.read_text()
        supported = function(source, "rlcn20_mux_supported")
        self.assertIn('dmi_match(DMI_PRODUCT_NAME, "83LT")', supported)
        self.assertIn("priv->conf != &model_rlcn", supported)
        self.assertIn("!strcmp(bios, rlcn_mux_bios_versions[i])", supported)
        table = re.search(
            r"static const char \* const rlcn_mux_bios_versions\[\] = \{(.*?)\};",
            source,
            re.S,
        )
        self.assertIsNotNone(table)
        self.assertEqual(tuple(re.findall(r'"(RLCN\d+WW)"', table.group(1))), ALLOWED_BIOS)
        config = re.search(
            r"^static const struct model_config model_rlcn = \{.*?^\};",
            source,
            re.M | re.S,
        )
        assert config is not None
        self.assertNotIn("leave_gamezone_wmi_unbound", config.group())
        self.assertNotIn("allow_rlcn20_uma_write", source)
        self.assertNotIn("efivar_set_variable", source)
        get = function(source, "rlcn20_get_graphics_mode")
        self.assertIn("return -EOPNOTSUPP;", get.split("#else")[1])
        self.assertNotIn("rlcn20_wmi_get_gsync", get)

        code = BIOS_HARNESS.replace("__TABLE__", table.group(0)).replace(
            "__FUNCTION__", supported
        )
        with tempfile.TemporaryDirectory() as tmp:
            src, binary = Path(tmp) / "bios_test.c", Path(tmp) / "bios_test"
            src.write_text(code)
            subprocess.run(
                ["gcc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                 str(src), "-o", str(binary)],
                check=True,
            )
            subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    unittest.main()
