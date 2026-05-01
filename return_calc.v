module return_calc (
    input clk, rst_n,
    input [15:0] price_new,
    input start_calc,
    output reg [31:0] return_val
);
    reg [15:0] price_old;
    reg first_run;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            price_old <= 0;
            return_val <= 0;
            first_run <= 1;
        end else if (start_calc) begin
            if (first_run) begin
                price_old <= price_new;
                first_run <= 0;
                return_val <= 0;
            end else begin
                // Calculate difference and scale up (Shift left 8) 
                // to make the number "visible" to the Jacobi solver
                return_val <= (price_new - price_old) <<< 8;
                price_old <= price_new;
            end
        end
    end
endmodule