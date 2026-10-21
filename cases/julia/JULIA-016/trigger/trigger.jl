println("JULIA-TRIGGER-START")
using Test
using JuliaSyntax

function diagnostics_for(code)
    stream = JuliaSyntax.ParseStream(code; version=v"1.6")
    JuliaSyntax.parse!(stream, rule=:all)
    stream.diagnostics
end

@testset "JULIA-016 import-path diagnostics" begin
    @test isempty(diagnostics_for("import A: (..)"))
    @test only(diagnostics_for("import :A")).message == "expected identifier"
end

println("JULIA-016 trigger completed")
