using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")
@testset "peek_behind_pos with negative byte index" begin
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parseall(JuliaSyntax.GreenNode, "do")
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parseall(JuliaSyntax.GreenNode, "do ")
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parseall(JuliaSyntax.GreenNode, " do")
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parseall(JuliaSyntax.GreenNode, "do\n")
end
