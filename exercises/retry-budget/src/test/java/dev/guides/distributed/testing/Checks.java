package dev.guides.distributed.testing;

import java.util.Objects;

public final class Checks {
    private Checks() {
    }

    public static void isTrue(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    public static void isFalse(boolean condition, String message) {
        isTrue(!condition, message);
    }

    public static void equals(Object expected, Object actual, String message) {
        if (!Objects.equals(expected, actual)) {
            throw new AssertionError(
                message + " (expected=" + expected + ", actual=" + actual + ")"
            );
        }
    }

    public static void same(Object expected, Object actual, String message) {
        if (expected != actual) {
            throw new AssertionError(message);
        }
    }

    public static <T extends Throwable> T throwsType(
        Class<T> type,
        ThrowingRunnable action,
        String message
    ) {
        try {
            action.run();
        } catch (Throwable error) {
            if (type.isInstance(error)) {
                return type.cast(error);
            }
            throw new AssertionError(
                message + " (expected=" + type.getName()
                    + ", actual=" + error.getClass().getName() + ")",
                error
            );
        }
        throw new AssertionError(message + " (no exception)");
    }

    public static void contains(String text, String fragment, String message) {
        if (text == null || !text.contains(fragment)) {
            throw new AssertionError(
                message + " (fragment=" + fragment + ", text=" + text + ")"
            );
        }
    }

    @FunctionalInterface
    public interface ThrowingRunnable {
        void run() throws Exception;
    }
}
