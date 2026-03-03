fn main() {
    let val = 0u8;
    // Use the safe, idiomatic trailing_zeros() method which is defined for all values,
    // including zero, where it returns the number of bits in the type.
    let result = val.trailing_zeros();
    println!("{}", result);
}