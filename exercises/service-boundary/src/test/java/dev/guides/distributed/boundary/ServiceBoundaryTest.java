package dev.guides.distributed.boundary;

import dev.guides.distributed.testing.Checks;
import java.util.List;
import java.util.Set;

public final class ServiceBoundaryTest {
    public static void main(String[] args) {
        validOwnershipAndDirectionPass();
        sharedWriteAndMissingOwnerWriterFail();
        unknownReferencesFail();
        System.out.println("service-boundary tests passed");
    }

    private static ServiceBoundary.Service service(String name, String... dependencies) {
        return new ServiceBoundary.Service(name, Set.of(dependencies));
    }

    private static void validOwnershipAndDirectionPass() {
        ServiceBoundary.Architecture architecture = new ServiceBoundary.Architecture(
            List.of(
                service("gateway", "reservation"),
                service("reservation", "inventory"),
                service("inventory")
            ),
            List.of(
                new ServiceBoundary.DataSet("reservations", "reservation", Set.of("reservation")),
                new ServiceBoundary.DataSet("stock", "inventory", Set.of("inventory"))
            )
        );

        Checks.equals(
            List.of(),
            ServiceBoundary.review(architecture),
            "Single-writer ownership with an acyclic dependency direction must pass"
        );
    }

    private static void sharedWriteAndMissingOwnerWriterFail() {
        ServiceBoundary.Architecture architecture = new ServiceBoundary.Architecture(
            List.of(service("reservation"), service("inventory")),
            List.of(
                new ServiceBoundary.DataSet(
                    "stock",
                    "inventory",
                    Set.of("inventory", "reservation")
                ),
                new ServiceBoundary.DataSet("reservations", "reservation", Set.of())
            )
        );

        String issues = String.join("\n", ServiceBoundary.review(architecture));
        Checks.contains(issues, "non-owner writer for stock", "Shared writes must be reported");
        Checks.contains(
            issues,
            "owner is not a writer for reservations",
            "An owner missing from the writer set must be reported"
        );
    }

    private static void unknownReferencesFail() {
        ServiceBoundary.Architecture architecture = new ServiceBoundary.Architecture(
            List.of(service("reservation", "missing-service")),
            List.of(
                new ServiceBoundary.DataSet("audit", "missing-owner", Set.of("missing-writer"))
            )
        );

        String issues = String.join("\n", ServiceBoundary.review(architecture));
        Checks.contains(issues, "unknown owner", "Unknown owners must be reported");
        Checks.contains(issues, "unknown writer", "Unknown writers must be reported");
        Checks.contains(issues, "unknown dependency", "Unknown dependencies must be reported");
    }

}
