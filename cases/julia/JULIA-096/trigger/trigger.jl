println("JULIA-TRIGGER-START")
using Test
using JuliaSyntax

@testset "JULIA-096 toplevel line numbers after blank line" begin
    @test JuliaSyntax.parseall(Expr, "a\n\nx") ==
        Expr(:toplevel, LineNumberNode(1), :a, LineNumberNode(3), :x)
    @test JuliaSyntax.parseall(Expr, "a\n\nx;y") ==
        Expr(:toplevel, LineNumberNode(1), :a, LineNumberNode(3), Expr(:toplevel, :x, :y))
end
