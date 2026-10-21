println("JULIA-TRIGGER-START")
module Julia271OptionalConfig

using Test
using Comonicon
using Configurations

@option struct Opts
    x::String = "x"
end

@main function main(; config::Opts=Opts())
    @test config == Opts("x")
end

end

Julia271OptionalConfig.command_main(String[])
println("JULIA-271 trigger completed")
