using JLD2
mutable struct MisreportedIO <: IO
    inner::IOBuffer
end
Base.position(x::MisreportedIO) = position(x.inner)
Base.seek(x::MisreportedIO, n::Integer) = seek(x.inner,n)
Base.seekend(x::MisreportedIO) = seekend(x.inner)
Base.seekstart(x::MisreportedIO) = seekstart(x.inner)
Base.read(x::MisreportedIO, args...) = read(x.inner, args...)
Base.readbytes!(x::MisreportedIO, args...) = readbytes!(x.inner, args...)
Base.unsafe_read(x::MisreportedIO, p::Ptr{UInt8}, n::UInt) = unsafe_read(x.inner,p,n)
Base.write(x::MisreportedIO, args...) = write(x.inner,args...)
Base.unsafe_write(x::MisreportedIO, p::Ptr{UInt8}, n::UInt) = unsafe_write(x.inner,p,n)
Base.truncate(x::MisreportedIO, n::Integer) = truncate(x.inner,n)
Base.flush(x::MisreportedIO) = flush(x.inner)
Base.close(x::MisreportedIO) = nothing
Base.isreadable(::MisreportedIO) = true
Base.iswritable(::MisreportedIO) = true
JLD2.isseekable(::MisreportedIO) = true
Base.bytesavailable(x::MisreportedIO) = bytesavailable(x.inner)
Base.filesize(::MisreportedIO) = 0
println("JULIA-TRIGGER-START")
inner = IOBuffer(UInt8[1,2,3,4,5])
seek(inner, 2)
rw = JLD2.RWBuffer(MisreportedIO(inner))
if rw.size != 5
    error("RWBuffer size does not reflect seekable stream length: $(rw.size)")
end
println("JULIA-747 trigger completed")
