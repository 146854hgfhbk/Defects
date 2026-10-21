# JULIA-660 trigger: AbstractString support in escapeuri (URIs PR #48, issue #42).
# The assertion is verbatim from the upstream fixed test and calls public API only.
using URIs
using Test
println("JULIA-TRIGGER-START")

struct CustomString <: AbstractString
    str::String
end

Base.codeunits(x::CustomString) = codeunits(x.str)

@testset "JULIA-660 AbstractString escapeuri MWE" begin
    @test URIs.escapeuri(CustomString("http://example.com")) == URIs.escapeuri("http://example.com")
end

println("JULIA-660 trigger completed")
