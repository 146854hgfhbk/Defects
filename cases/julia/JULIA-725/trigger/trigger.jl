using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")

@testset "invalid string interpolation syntax" begin
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parsestmt(
        Expr, "\"\$(x,y)\""
    )
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parsestmt(
        Expr, "\"\$(x;y)\""
    )
end

println("JULIA-725 trigger completed")
