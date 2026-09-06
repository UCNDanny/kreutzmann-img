import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;

/** Starts the optimized Keycloak distribution in the same JVM, without a shell. */
public final class KeycloakLauncher {
    public static void main(String[] args) throws Exception {
        Path ca = Path.of("/tmp/database-ca.pem");
        String privateCa = System.getenv("DATABASE_CA_PEM");
        byte[] certificates = privateCa == null || privateCa.isBlank()
            ? Files.readAllBytes(Path.of("/etc/ssl/certs/public-ca-bundle.pem"))
            : (privateCa + "\n").getBytes(java.nio.charset.StandardCharsets.UTF_8);
        if (!Files.exists(ca)) {
            Files.createFile(ca, PosixFilePermissions.asFileAttribute(
                PosixFilePermissions.fromString("rw-------")));
        }
        Files.write(ca, certificates);
        System.setProperty("kc.script.pid", Long.toString(ProcessHandle.current().pid()));
        Class.forName("io.quarkus.bootstrap.runner.QuarkusEntryPoint")
            .getMethod("main", String[].class).invoke(null, (Object) args);
    }
}
