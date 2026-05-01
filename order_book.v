module order_book (
    input        clk,
    input        rst_n,
    input  [15:0] in_price_s1,
    input  [15:0] in_price_s2,
    input        update_en,

    output reg [15:0] s1_reg,
    output reg [15:0] s2_reg,
    output reg        start_calc
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_reg <= 0;
            s2_reg <= 0;
            start_calc <= 0;
        end else begin
            start_calc <= 0;

            if (update_en) begin
                s1_reg <= in_price_s1;
                s2_reg <= in_price_s2;
                start_calc <= 1'b1;   // 1-cycle trigger
            end
        end
    end

endmodule