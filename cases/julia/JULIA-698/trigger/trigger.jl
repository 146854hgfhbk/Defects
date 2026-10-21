using Test
using Makie

println("JULIA-TRIGGER-START")
@testset "volume bounding box" begin
    _, _, plot = volume(rand(5, 5, 5))
    box = boundingbox(plot)
    @test box.origin ≈ Point3f(0)
    @test box.widths ≈ Vec3f(5)
end
