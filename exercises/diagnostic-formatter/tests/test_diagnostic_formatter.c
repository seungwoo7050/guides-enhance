#include "diagnostic_formatter.h"

#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define CHECK(expression)                                                   \
    do                                                                      \
    {                                                                       \
        if (!(expression))                                                  \
        {                                                                   \
            fprintf(stderr, "%s:%d: check failed: %s\n",                  \
                    __FILE__, __LINE__, #expression);                       \
            return 1;                                                       \
        }                                                                   \
    } while (0)

static int call_twice(
    char *first,
    char *second,
    size_t capacity,
    const char *format,
    ...
) {
    int left;
    int right;
    va_list arguments;

    va_start(arguments, format);
    left = diagnostic_vformat(first, capacity, format, arguments);
    right = diagnostic_vformat(second, capacity, format, arguments);
    va_end(arguments);
    return left == right ? left : -1;
}

int main(void) {
    char buffer[128];
    char tiny[5];
    char exact[7];
    char short_exact[6];
    char first[32];
    char second[32];
    int result;

    result = diagnostic_format(buffer, sizeof buffer, "");
    CHECK(result == 0 && strcmp(buffer, "") == 0);

    result = diagnostic_format(buffer, sizeof buffer, "%% %%");
    CHECK(result == 3 && strcmp(buffer, "% %") == 0);

    result = diagnostic_format(buffer, sizeof buffer, "hello %s %d %%", "world", -42);
    CHECK(result == 17 && strcmp(buffer, "hello world -42 %") == 0);

    result = diagnostic_format(buffer, sizeof buffer, "%d %d %d", 0, INT_MIN, INT_MAX);
    CHECK(result == (int)strlen(buffer));

    result = diagnostic_format(buffer, sizeof buffer, "x=%s", (const char *)NULL);
    CHECK(result == 8 && strcmp(buffer, "x=(null)") == 0);

    result = diagnostic_format(exact, sizeof exact, "abcdef");
    CHECK(result == 6 && strcmp(exact, "abcdef") == 0);

    result = diagnostic_format(short_exact, sizeof short_exact, "abcdef");
    CHECK(result == 6 && strcmp(short_exact, "abcde") == 0);
    CHECK(short_exact[sizeof short_exact - 1] == '\0');

    result = diagnostic_format(tiny, sizeof tiny, "abcdef");
    CHECK(result == 6 && strcmp(tiny, "abcd") == 0);
    CHECK(tiny[sizeof tiny - 1] == '\0');

    buffer[0] = 'x';
    result = diagnostic_format(buffer, 1, "abc");
    CHECK(result == 3 && buffer[0] == '\0');

    CHECK(diagnostic_format(NULL, 0, "abc%d", 7) == 4);
    buffer[0] = 'Q';
    CHECK(diagnostic_format(buffer, 0, "abc%d", 7) == 4);
    CHECK(buffer[0] == 'Q');
    CHECK(diagnostic_format(NULL, 1, "x") == -1);
    CHECK(diagnostic_format(buffer, sizeof buffer, NULL) == -1);

    strcpy(buffer, "untouched-after-prefix?");
    CHECK(diagnostic_format(buffer, sizeof buffer, "%x", 1) == -1);
    CHECK(strcmp(buffer, "") == 0);
    CHECK(diagnostic_format(buffer, sizeof buffer, "ok:%x", 1) == -1);
    CHECK(strcmp(buffer, "ok:") == 0);
    CHECK(diagnostic_format(buffer, sizeof buffer, "trailing%") == -1);
    CHECK(strcmp(buffer, "trailing") == 0);

    result = call_twice(first, second, sizeof first, "%s:%d", "value", 7);
    CHECK(result == 7);
    CHECK(strcmp(first, "value:7") == 0 && strcmp(second, "value:7") == 0);

    result = call_twice(first, second, 5, "%s:%d", "value", 7);
    CHECK(result == 7);
    CHECK(strcmp(first, "valu") == 0 && strcmp(second, "valu") == 0);

    puts("diagnostic-formatter tests passed");
    return 0;
}
