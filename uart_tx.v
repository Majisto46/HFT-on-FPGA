module uart_tx (
    input       clk,        // 50MHz
    input       tx_start,   // Pulse to start sending
    input [7:0] tx_byte,    // Byte to send
    output reg  tx_serial,
    output      tx_done
);
    parameter CLKS_PER_BIT = 434;
    reg [15:0] clk_cnt = 0;
    reg [2:0]  state   = 0;
    reg [2:0]  bit_idx = 0;
    reg [7:0]  tx_data = 0;

    assign tx_done = (state == 0);

    always @(posedge clk) begin
        case (state)
            0: begin // Idle
                tx_serial <= 1'b1;
                if (tx_start) begin
                    tx_data <= tx_byte;
                    state   <= 1;
                end
            end
            1: begin // Start Bit (0)
                tx_serial <= 1'b0;
                if (clk_cnt < CLKS_PER_BIT-1) clk_cnt <= clk_cnt + 1;
                else begin clk_cnt <= 0; state <= 2; end
            end
            2: begin // Data Bits
                tx_serial <= tx_data[bit_idx];
                if (clk_cnt < CLKS_PER_BIT-1) clk_cnt <= clk_cnt + 1;
                else begin
                    clk_cnt <= 0;
                    if (bit_idx < 7) bit_idx <= bit_idx + 1;
                    else begin bit_idx <= 0; state <= 3; end
                end
            end
            3: begin // Stop Bit (1)
                tx_serial <= 1'b1;
                if (clk_cnt < CLKS_PER_BIT-1) clk_cnt <= clk_cnt + 1;
                else begin clk_cnt <= 0; state <= 0; end
            end
        endcase
    end
endmodule