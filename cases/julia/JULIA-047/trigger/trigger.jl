using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")
@testset "command macro suffix" begin
    @test JuliaSyntax.parsestmt(Expr, "foo`str`flag") ==
        Expr(:macrocall, Symbol("@foo_cmd"), LineNumberNode(1), "str", "flag")
end
