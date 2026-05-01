`timescale 1ns/1ps

module tb_order_book;

  reg clk, rst_n;
  reg [15:0] in_price_s1, in_price_s2;
  reg update_en;

  wire [15:0] s1_reg, s2_reg;
  wire start_calc;

  order_book dut (
    .clk(clk),
    .rst_n(rst_n),
    .in_price_s1(in_price_s1),
    .in_price_s2(in_price_s2),
    .update_en(update_en),
    .s1_reg(s1_reg),
    .s2_reg(s2_reg),
    .start_calc(start_calc)
  );

  always #5 clk = ~clk;

  initial begin
    clk = 0; rst_n = 0;
    update_en = 0;

    #20 rst_n = 1;

    @(posedge clk);
    in_price_s1 = 100;
    in_price_s2 = 95;
    update_en = 1;

    @(posedge clk);
    update_en = 0;

    #100 $stop;
  end

endmodule