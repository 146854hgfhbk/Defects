using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")

@testset "GreenNode equality and hashing contract" begin
    x = JuliaSyntax.parse(JuliaSyntax.GreenNode, "1 + 1")
    y = JuliaSyntax.parse(JuliaSyntax.GreenNode, "1 + 1")
    @test x == y
    @test hash(x) == hash(y)
    @test haskey(Dict(x => :present), y)
end

println("JULIA-746 trigger completed")
