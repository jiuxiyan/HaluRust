fn main() {
    // Use wrapping_sub to avoid UB; 30000 - (-7000) wraps to -28536
    let _val = 30000i16.wrapping_sub(-7000);
}