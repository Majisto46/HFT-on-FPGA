module hft_top (
    input          clk,           // 50MHz - PIN_P11
    input          rst_n,         // Reset  - PIN_B8
    input  [1:0]   KEY,           // KEY[1]=PIN_A7, KEY[0]=PIN_B8
    input          uart_rx_line,  // RX     - PIN_V10
    input  [9:0]   SW,            // SW[9]  - PIN_F15
    output [6:0]   HEX0, HEX1, HEX2, HEX3, HEX4, HEX5,
    output [9:0]   LEDR,          // L9=Busy, L8=RX, L0=TX
    output         uart_tx_line   // TX     - PIN_W10
);

    // --- Signals ---
    wire [7:0]  w_rx_byte;
    wire        w_rx_dv, w_parser_vld, w_jacobi_done;
    wire [15:0] w_s1, w_s2;
    wire [31:0] s1_ret, s2_ret, cov_val, eigen1, total_profit;
    wire [7:0]  trade_state;     // <--- ADDED THIS LINE: Declares the missing object
    wire        w_start_math, cov_ready;
    reg  [23:0] r_display_buffer;
    reg         r_busy;

    // --- 1. RX Input Filter ---
    reg [1:0] rx_sync;
    always @(posedge clk) rx_sync <= {rx_sync[0], uart_rx_line};
    
    uart_rx rx_inst (
        .clk(clk), .rx_serial(rx_sync[1]), .rx_byte(w_rx_byte), .rx_dv(w_rx_dv)
    );

    // --- 2. Parser ---
    Parser parser_inst (
        .clk(clk), .rst_n(rst_n), 
        .uart_data(w_rx_byte), .uart_ready(w_rx_dv && !r_busy),
        .price_s1(w_s1), .price_s2(w_s2), .data_valid(w_parser_vld)
    );

    // --- 3. Busy Logic ---
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r_busy <= 0;
        else if (w_parser_vld) r_busy <= 1;
        else if (w_jacobi_done) r_busy <= 0;
    end

    // --- 4. Math Engine Pipeline ---
    assign w_start_math = w_parser_vld;

    return_calc rc1 (.clk(clk), .rst_n(rst_n), .price_new(w_s1), .start_calc(w_start_math), .return_val(s1_ret));
    return_calc rc2 (.clk(clk), .rst_n(rst_n), .price_new(w_s2), .start_calc(w_start_math), .return_val(s2_ret));
    
    covariance_engine cov_inst (
        .clk(clk), .rst_n(rst_n), .return_s1(s1_ret), .return_s2(s2_ret), 
        .calc_done(w_start_math), .cov_out(cov_val), .cov_ready(cov_ready)
    );

    jacobi_solver jacobi_inst (
        .clk(clk), .rst_n(rst_n), .var1(s1_ret), .var2(s2_ret), .cov12(cov_val), 
        .start(cov_ready), .eigen1(eigen1), .done(w_jacobi_done)
    );

    // Updated port_inst to output the trade_state
    portfolio_manager port_inst (
        .clk(clk), .rst_n(rst_n), 
        .data_valid(w_jacobi_done), 
        .eigen1(eigen1), 
        .trade_state(trade_state),   // <--- CONNECTED TO THE WIRE
        .total_profit(total_profit)
    );

    // --- 5. UART TX ---
    reg [7:0] r_tx_byte;
    reg r_tx_en;

    always @(posedge clk) begin
        if (w_jacobi_done) begin
            r_tx_byte <= trade_state; 
            r_tx_en <= 1;
        end else begin
            r_tx_en <= 0;
        end
    end

    uart_tx tx_inst (
        .clk(clk), .tx_start(r_tx_en), 
        .tx_byte(r_tx_byte), .tx_serial(uart_tx_line)
    );

    // --- 6. Debug Displays ---
    always @(posedge clk) if (w_jacobi_done) r_display_buffer <= total_profit[23:0];

    seven_seg_decoder h0 (.bin(r_display_buffer[3:0]),   .seg(HEX0));
    seven_seg_decoder h1 (.bin(r_display_buffer[7:4]),   .seg(HEX1));
    seven_seg_decoder h2 (.bin(r_display_buffer[11:8]),  .seg(HEX2));
    seven_seg_decoder h3 (.bin(r_display_buffer[15:12]), .seg(HEX3));
    seven_seg_decoder h4 (.bin(r_display_buffer[19:16]), .seg(HEX4));
    seven_seg_decoder h5 (.bin(r_display_buffer[23:20]), .seg(HEX5));

    assign LEDR[9] = r_busy;
    assign LEDR[8] = rx_sync[1];
    assign LEDR[0] = uart_tx_line;

endmodule