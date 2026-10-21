using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")

@testset "incomplete function reports ParseError" begin
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parseall(
        JuliaSyntax.GreenNode, "function"
    )
end

println("JULIA-730 trigger completed")
