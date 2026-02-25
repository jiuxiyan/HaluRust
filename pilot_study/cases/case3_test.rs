#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_array() {
        let arr = create_array();
        assert_eq!(arr[0], 0);
        assert_eq!(arr[1], 10);
        assert_eq!(arr[2], 20);
    }
}
