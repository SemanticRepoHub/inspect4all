public class Calculator {
    private final int offset;
    public Calculator(int offset) { this.offset = offset; }
    public int add(int a, int b) { return a + b + offset; }
    public static void main(String[] args) {
        System.out.println(new Calculator(1).add(2, 3));
    }
}
