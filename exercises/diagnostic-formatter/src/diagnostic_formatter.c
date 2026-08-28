#include "diagnostic_formatter.h"

#include <limits.h>
#include <stdint.h>

/* [Implementation 1] Output buffer and logical length */
struct output {
    char *buffer;
    size_t capacity;
    size_t length;
    int failed;
};

static void output_char(struct output *output, char value) {
    if (output->failed) {
        return;
    }
    if (output->length == SIZE_MAX) {
        output->failed = 1;
        return;
    }
    // 실제 기록이 끝나도 반환할 전체 필요 길이는 계속 계산합니다.
    if (output->capacity > 0 && output->length < output->capacity - 1) {
        output->buffer[output->length] = value;
    }
    output->length++;
}

/* [Implementation 2] String and integer emitters */
static void output_text(struct output *output, const char *text) {
    if (text == NULL) {
        text = "(null)";
    }
    while (*text != '\0') {
        output_char(output, *text);
        text++;
    }
}

static void output_unsigned(struct output *output, unsigned int value) {
    char digits[sizeof value * CHAR_BIT];
    size_t count = 0;

    do {
        digits[count++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value != 0u);
    while (count > 0) {
        output_char(output, digits[--count]);
    }
}

static void output_int(struct output *output, int value) {
    unsigned int magnitude;

    if (value < 0) {
        output_char(output, '-');
        magnitude = 0u - (unsigned int)value;
    } else {
        magnitude = (unsigned int)value;
    }
    output_unsigned(output, magnitude);
}

/* [Implementation 3] NUL termination after truncation */
static void finish_output(struct output *output) {
    size_t index;

    if (output->capacity == 0 || output->buffer == NULL) {
        return;
    }
    index = output->length;
    if (index >= output->capacity) {
        index = output->capacity - 1;
    }
    output->buffer[index] = '\0';
}

/* [Implementation 4] Format parsing with a copied va_list */
int diagnostic_vformat(
    char *buffer,
    size_t capacity,
    const char *format,
    va_list arguments
) {
    struct output output = {buffer, capacity, 0, 0};
    va_list copy;

    if (format == NULL || (capacity > 0 && buffer == NULL)) {
        return -1;
    }
    va_copy(copy, arguments);
    while (*format != '\0' && !output.failed) {
        if (*format != '%') {
            output_char(&output, *format++);
            continue;
        }
        format++;
        if (*format == '%') {
            output_char(&output, '%');
        } else if (*format == 's') {
            output_text(&output, va_arg(copy, const char *));
        } else if (*format == 'd') {
            output_int(&output, va_arg(copy, int));
        } else {
            output.failed = 1;
            break;
        }
        format++;
    }
    va_end(copy);
    finish_output(&output);
    if (output.failed || output.length > (size_t)INT_MAX) {
        return -1;
    }
    return (int)output.length;
}

/* [Implementation 5] Variadic wrapper */
int diagnostic_format(
    char *buffer,
    size_t capacity,
    const char *format,
    ...
) {
    int result;
    va_list arguments;

    va_start(arguments, format);
    result = diagnostic_vformat(buffer, capacity, format, arguments);
    va_end(arguments);
    return result;
}
