fn main() {
    let val: u8 = 2;
    // Safely convert u8 to bool: non-zero becomes true
    let b = val != 0;
    let _x = b == std::hint::black_box(true);
}