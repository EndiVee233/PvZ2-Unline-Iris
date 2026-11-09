// Export the Iris ARM input functions and the analysis function index.
//@category Iris

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class ExportIrisNative extends GhidraScript {
    private static final String[][] TARGETS = {
        {"009eadb8", "jni_on_load"},
        {"009eb5e4", "jni_on_unload"},
        {"009f0298", "touch_dispatch"},
        {"009d9390", "touch_coordinates"},
        {"001841fc", "board_touch_coordinates"},
        {"009e8208", "touch_began"},
        {"009e8378", "touch_moved"},
        {"009e8528", "touch_ended"},
        {"009e8828", "touch_cancelled"},
    };

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1 || !"libPVZ2.so".equals(currentProgram.getName())) {
            throw new IllegalArgumentException("Run on the baseline libPVZ2.so and pass an output directory");
        }
        Path output = Files.createDirectories(Paths.get(args[0]));
        Address base = currentProgram.getImageBase();
        if (currentProgram.getMemory().getInt(base.add(0x009f0298)) != 0xe92d4800) {
            throw new IllegalStateException("The Iris touch dispatcher does not match the NA baseline");
        }
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) {
                throw new IllegalStateException(decompiler.getLastMessage());
            }
            for (String[] target : TARGETS) {
                monitor.checkCancelled();
                Address entry = base.add(Long.parseLong(target[0], 16));
                Function function = getFunctionAt(entry);
                if (function == null) {
                    disassemble(entry);
                    function = createFunction(entry, null);
                }
                if (function == null) {
                    throw new IllegalStateException("Cannot locate function at " + entry);
                }
                DecompileResults result = decompiler.decompileFunction(function, 45, monitor);
                if (!result.decompileCompleted()) {
                    throw new IllegalStateException(entry + " " + result.getErrorMessage());
                }
                try (BufferedWriter writer = Files.newBufferedWriter(output.resolve(target[1] + ".c"))) {
                    writer.write("/* Ghidra pseudocode at ELF address " + target[0] + ".\n");
                    for (Reference reference : getReferencesTo(entry)) {
                        Address from = reference.getFromAddress();
                        String location = from.getAddressSpace().equals(base.getAddressSpace())
                            ? "ELF 0x" + Long.toHexString(from.subtract(base)) : from.toString();
                        writer.write(" * " + reference.getReferenceType() + " from " + location + "\n");
                    }
                    writer.write(" */\n");
                    writer.write(result.getDecompiledFunction().getC());
                }
            }
        } finally {
            decompiler.dispose();
        }
        try (BufferedWriter writer = Files.newBufferedWriter(output.resolve("functions.tsv"))) {
            writer.write("elf_address\tname\n");
            for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
                monitor.checkCancelled();
                Address entry = function.getEntryPoint();
                if (entry.getAddressSpace().equals(base.getAddressSpace())) {
                    writer.write(Long.toHexString(entry.subtract(base)) + "\t" + function.getName(true) + "\n");
                }
            }
        }
    }
}
