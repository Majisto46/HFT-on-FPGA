module covariance_engine (
    input clk, rst_n,
    input [31:0] return_s1, return_s2,
    input calc_done, // Trigger from return_calc
    output reg [31:0] cov_out,
    output reg cov_ready
);
    reg [63:0] product;
    reg [1:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= 0;
            cov_ready <= 0;
            cov_out <= 0;
        end else begin
            case (state)
                0: begin
                    cov_ready <= 0;
                    if (calc_done) begin
                        product <= return_s1 * return_s2;
                        state <= 1;
                    end
                end
                1: begin
                    // Scale down the result (adjust shift based on your fixed-point)
                    cov_out <= product[47:16]; 
                    state <= 2;
                end
                2: begin
                    cov_ready <= 1'b1; // Pulse Start
                    state <= 3;
                end
                3: begin
                    cov_ready <= 1'b0; // Pulse End (Critical Fix)
                    state <= 0;
                end
            endcase
        end
    end
endmodule