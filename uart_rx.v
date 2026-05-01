module uart_rx (
    input        clk,      // 50MHz
    input        rx_serial,
    output reg [7:0] rx_byte,
    output reg       rx_dv
);
    parameter CLKS_PER_BIT = 434; // 50MHz / 115200

    reg [15:0] clk_cnt = 0;
    reg [2:0]  bit_idx = 0;
    reg [7:0]  rx_data = 0;
    reg [2:0]  state   = 0;

    always @(posedge clk) begin
        case (state)
            0: begin // Idle - Wait for Start Bit (0)
                rx_dv   <= 0;
                clk_cnt <= 0;
                bit_idx <= 0;
                if (rx_serial == 0) state <= 1;
            end
            1: begin // Verify Start Bit (Middle)
                if (clk_cnt == (CLKS_PER_BIT-1)/2) begin
                    if (rx_serial == 0) begin
                        clk_cnt <= 0;
                        state   <= 2;
                    end else state <= 0;
                end else clk_cnt <= clk_cnt + 1;
            end
            2: begin // Sample 8 Data Bits
                if (clk_cnt < CLKS_PER_BIT-1) clk_cnt <= clk_cnt + 1;
                else begin
                    clk_cnt <= 0;
                    rx_data[bit_idx] <= rx_serial;
                    if (bit_idx < 7) bit_idx <= bit_idx + 1;
                    else state <= 3;
                end
            end
            3: begin // Stop Bit (1)
                if (clk_cnt < CLKS_PER_BIT-1) clk_cnt <= clk_cnt + 1;
                else begin
                    rx_dv   <= 1;
                    rx_byte <= rx_data;
                    state   <= 0;
                end
            end
            default: state <= 0;
        endcase
    end
endmodule