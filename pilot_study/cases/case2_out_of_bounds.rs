/// Case 2: Out-of-bounds access via raw pointer arithmetic
/// Pointer arithmetic goes beyond allocated memory.

pub fn sum_array(data: &[i32]) -> i32 {
    let ptr = data.as_ptr();
    let mut sum = 0i32;
    for i in 0..=data.len() {
        // Off-by-one: reads one element past the end
        sum += unsafe { *ptr.add(i) };
    }
    sum
}
