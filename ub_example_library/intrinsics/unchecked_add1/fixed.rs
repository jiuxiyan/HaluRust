fn main() {
    // Use wrapping_add to avoid UB; result will be 4464 (70000 mod 65536)
    let _val = 40000u16.wrapping_add(30000);
}