using Test
using Nemo

println("JULIA-TRIGGER-START")

@testset "JULIA-717 composite-modulus matrix inverse" begin
    ring = ResidueRing(ZZ, 8)
    matrix_value = matrix(ring, 2, 2, [2, 1, 1, 2])
    @test isone(matrix_value * inv(matrix_value))
end
