using Test
using Graphs

println("JULIA-TRIGGER-START")
@testset "eulerian trail validates odd-degree start" begin
    path = SimpleGraph([Edge(1, 2), Edge(2, 3)])
    @test eulerian(path, 3) == [3, 2, 1]
    @test_throws ErrorException eulerian(path, 2)

    star = SimpleGraph([Edge(1, 2), Edge(1, 3), Edge(1, 4)])
    @test_throws ErrorException eulerian(star, 1)
end
