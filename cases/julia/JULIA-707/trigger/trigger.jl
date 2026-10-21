using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")
@testset "invalid catch binding is rejected" begin
    @test_throws JuliaSyntax.ParseError JuliaSyntax.parseall(
        JuliaSyntax.GreenNode,
        "try 3 catch e+3 end",
    )
end
println("JULIA-707 trigger completed")
