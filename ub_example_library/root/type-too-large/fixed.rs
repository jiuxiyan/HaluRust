fn main() {
    // Large allocations should be placed on the heap to avoid stack overflow 
    // and to satisfy compiler limits on type sizes.
    // We use a size that is large but valid for the architecture's address space.
    let size: usize = 1usize << 30; // 1 GiB
    
    // Using a Vec ensures the allocation happens on the heap.
    // This avoids the post-monomorphization error caused by excessively large stack types.
    let _fat = vec![0u8; size];
    
    println!("Successfully allocated {} bytes on the heap.", _fat.len());
}