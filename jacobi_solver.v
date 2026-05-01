module jacobi_solver (
    input clk, rst_n,
    input [31:0] var1, var2, cov12,
    input start,
    output reg [31:0] eigen1,
    output reg done
);
    reg [3:0] state;
    reg [63:0] term1, term2, radicand;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= 0; done <= 0; eigen1 <= 0;
        end else begin
            case (state)
                0: begin
                    done <= 0;
                    if (start) state <= 1;
                end
                1: begin
                    // (var1 - var2)^2
                    term1 <= (var1 > var2) ? (var1 - var2)**2 : (var2 - var1)**2;
                    state <= 2;
                end
                2: begin
                    // 4 * cov^2
                    term2 <= (cov12 * cov12) << 2;
                    state <= 3;
                end
                3: begin
                    radicand <= term1 + term2;
                    state <= 4;
                end
                4: begin
                    // Simple shift-based Square Root approx for stability
                    // In a real system, use an Altera IP Square Root block here
                    eigen1 <= (var1 + var2 + (radicand >> 32)) >> 1; 
                    state <= 5;
                end
                5: begin
                    done <= 1;
                    state <= 0;
                end
            endcase
        end
    end
endmodule