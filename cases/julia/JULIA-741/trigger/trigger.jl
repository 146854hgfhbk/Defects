using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")

@testset "const without assignment is rejected" begin
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parse(Expr, "const a")
end

println("JULIA-741 trigger completed")
