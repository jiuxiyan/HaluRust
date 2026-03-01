// Check that TB properly rejects alternating Reads and Writes, but tolerates
// alternating only Reads to Reserved mutable references.
fn main() {
    let x = &mut 0u8;
    // Reborrow x into y safely
    let y = &mut *x;
    
    // Read through y (instead of x) to keep y active
    let _val = *y;
    
    // Now we activate y, for this to succeed y needs to not have been Frozen
    // by the previous operation
    *y += 1; // Success
    
    // This time we also read through y instead of x to prevent y from being Frozen
    let _val = *y;
    
    // Now the next Write attempt succeeds because y was never frozen.
    *y += 1; // Success
    
    // Read through y again
    let _val = *y;
    
    // This write also succeeds
    *y += 1; // Success
    
    // Once we are done with y, we can use x again
    let _val = *x;
}