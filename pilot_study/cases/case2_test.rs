#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sum_array() {
        let data = vec![1, 2, 3, 4, 5];
        let result = sum_array(&data);
        assert_eq!(result, 15);
    }
}
