using JLD2
using Test

println("JULIA-TRIGGER-START")

@testset "JULIA-616 shared Shuffle configuration is not mutated" begin
    # Reusing a caller-owned compression pipeline is supported by jldopen.
    # The original configuration must remain reusable after the write.
    filters = [JLD2.Shuffle(), JLD2.Deflate()]
    data = collect(UInt32, 1:20_000)
    filename = joinpath(mktempdir(), "shared-shuffle.jld2")

    jldopen(filename, "w"; compress=filters) do file
        file["data"] = data
    end

    @test filters[1].element_size == 0
    @test jldopen(file -> file["data"], filename, "r") == data
end

println("JULIA-616 trigger completed")
