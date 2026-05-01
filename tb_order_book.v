`timescale 1ns/1ps

module tb_return_calc;

  reg clk, rst_n;
  reg [15:0] price_new;
  reg start_calc;

  wire [31:0] return_val;
  wire calc_done;

  return_calc dut (
    .clk(clk),
    .rst_n(rst_n),
    .price_new(price_new),
    .start_calc(start_calc),
    .return_val(return_val),
    .calc_done(calc_done)
  );

  always #5 clk = ~clk;

  initial begin
    clk = 0; rst_n = 0;
    start_calc = 0;

    #20 rst_n = 1;

    // first price (init)
    @(posedge clk);
    price_new = 100;
    start_calc = 1;
    @(posedge clk);
    start_calc = 0;

    // second price (calc)
    @(posedge clk);
    price_new = 105;
    start_calc = 1;
    @(posedge clk);
    start_calc = 0;

    #100 $stop;
  end

endmodule