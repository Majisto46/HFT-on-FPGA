module portfolio_manager (
    input clk, rst_n,
    input data_valid,
    input signed [31:0] eigen1, // Must be SIGNED to see negative moves
    output reg [7:0] trade_state,
    output reg [31:0] total_profit
);
    // Use a small threshold so it triggers easily
    parameter THRESHOLD = 32'sd50; 

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            trade_state <= 0;
            total_profit <= 0;
        end else if (data_valid) begin
            if (eigen1 > THRESHOLD) begin
                trade_state <= 8'd1; // 1 = BUY
                total_profit <= total_profit + (eigen1 >>> 8);
            end else if (eigen1 < -THRESHOLD) begin
                trade_state <= 8'd2; // 2 = SELL
                total_profit <= total_profit + (eigen1 >>> 8); // eigen1 is neg, so profit drops
            end else begin
                trade_state <= 8'd0; // 0 = SCANNING
            end
        end
    end
endmodule