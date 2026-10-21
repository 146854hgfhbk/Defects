using Test
using JuliaSyntax

println("JULIA-TRIGGER-START")
@testset "newline-terminated source locations" begin
    @test JuliaSyntax.source_location(JuliaSyntax.SourceFile("a\n"), 3) == (2, 1)
    @test JuliaSyntax.source_location(JuliaSyntax.SourceFile("a\nb\n"), 5) == (3, 1)
    @test JuliaSyntax.source_location(JuliaSyntax.SourceFile("\n\n"), 3) == (3, 1)
end
