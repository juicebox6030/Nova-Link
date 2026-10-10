"""Check the portable ESP-IDF source manifest without claiming a vendor build."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class PlatformPreparationTests(unittest.TestCase):
    def test_production_component_and_example_lifecycle(self):
        if shutil.which("cmake") is None:
            self.skipTest("cmake is unavailable")
        with tempfile.TemporaryDirectory(prefix="nova-platform-check-") as directory:
            work = pathlib.Path(directory)
            # Deliberately desktop-only: the vendor project itself is not mocked
            # or reported as an ESP-IDF build.
            (work / "esp_log.h").write_text(
                "#include <stdbool.h>\n"
                "void check_log(bool error, const char *format, ...);\n"
                "#define ESP_LOGI(tag, ...) check_log(false, __VA_ARGS__)\n"
                "#define ESP_LOGE(tag, ...) check_log(true, __VA_ARGS__)\n",
                encoding="utf-8",
            )
            (work / "runner.c").write_text(
                "#include <stdbool.h>\n#include <stdarg.h>\n"
                "#include <stdio.h>\n#include <string.h>\n"
                "static unsigned errors, completed;\n"
                "void app_main(void);\n"
                "void check_log(bool error, const char *format, ...) {\n"
                "  char text[256]; va_list args; va_start(args, format);\n"
                "  (void)vsnprintf(text, sizeof text, format, args); va_end(args);\n"
                "  if (error) ++errors;\n"
                "  if (strstr(text, \"manifest startup/poll/shutdown passed\")) ++completed;\n"
                "}\n"
                "int main(void) { app_main(); app_main();\n"
                "  return errors == 0 && completed == 2 ? 0 : 1; }\n",
                encoding="utf-8",
            )
            root = ROOT.as_posix()
            (work / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.16)\nproject(nova_platform_check C)\n"
                "function(idf_component_register)\n"
                "  cmake_parse_arguments(SOURCES \"\" \"\" \"SRCS;INCLUDE_DIRS\" ${ARGN})\n"
                "  foreach(source IN LISTS SOURCES_SRCS)\n"
                "    if(source MATCHES \"(multiverse_synthetic|plugin_conformance|fault_backend)\\\\.c$\")\n"
                "      message(FATAL_ERROR \"Developer source in production component\")\n"
                "    endif()\n"
                "  endforeach()\n"
                "  add_library(esp32 STATIC ${SOURCES_SRCS})\n"
                "  target_include_directories(esp32 PUBLIC ${SOURCES_INCLUDE_DIRS})\n"
                "  set(COMPONENT_LIB esp32 PARENT_SCOPE)\nendfunction()\n"
                f'add_subdirectory("{root}/platform/esp32" component)\n'
                f'add_executable(check runner.c "{root}/platform/esp32/example/main/main.c")\n'
                "target_include_directories(check PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})\n"
                "target_link_libraries(check PRIVATE esp32)\n"
                "set_target_properties(check esp32 PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED YES)\n",
                encoding="utf-8",
            )
            commands = [
                ["cmake", "-S", str(work), "-B", str(work / "build")],
                ["cmake", "--build", str(work / "build"), "--parallel", "2"],
                [str(work / "build" / "check")],
            ]
            for command in commands:
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
