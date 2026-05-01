module Parser (
    input clk, rst_n,
    input [7:0] uart_data,
    input uart_ready,
    output reg [15:0] price_s1, price_s2,
    output reg data_valid
);
    reg [1:0] byte_count;
    reg [31:0] shift_reg;
    reg [23:0] timeout_cnt; // Watchdog timer

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            byte_count <= 0;
            data_valid <= 0;
            timeout_cnt <= 0;
        end else begin
            data_valid <= 0; // Default pulse
            
            // Watchdog: If no data for ~0.2s, reset the byte counter
            if (uart_ready) begin
                timeout_cnt <= 0;
                shift_reg <= {shift_reg[23:0], uart_data};
                if (byte_count == 3) begin
                    price_s1 <= shift_reg[31:16];
                    price_s2 <= {shift_reg[7:0], uart_data}; // Grab current byte
                    data_valid <= 1;
                    byte_count <= 0;
                end else begin
                    byte_count <= byte_count + 1;
                end
            end else if (byte_count > 0) begin
                if (timeout_cnt > 10000000) begin
                    byte_count <= 0; // Reset stale packet
                    timeout_cnt <= 0;
                end else begin
                    timeout_cnt <= timeout_cnt + 1;
                end
            end
        end
    end
endmodule