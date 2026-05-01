`timescale 1ns/1ps

module tb_hft_top;

  //----------------------
  // Clock & Reset
  //----------------------
  reg clk;
  reg rst_n;

  //----------------------
  // UART input (unused in SIM)
  //----------------------
  reg uart_rx_line;

  //----------------------
  // DUT Outputs
  //----------------------
  wire [15:0] current_price_s1;
  wire [15:0] current_price_s2;

  wire [31:0] s1_return_val;
  wire [31:0] s2_return_val;

  wire [31:0] covariance_val;

  // NEW (Jacobi outputs)
  wire [31:0] eigen1;
  wire [31:0] eigen2;

  wire calc_finished_pulse;

  //----------------------
  // DUT
  //----------------------
  hft_top dut (
      .clk(clk),
      .rst_n(rst_n),
      .uart_rx_line(uart_rx_line),

      .current_price_s1(current_price_s1),
      .current_price_s2(current_price_s2),

      .s1_return_val(s1_return_val),
      .s2_return_val(s2_return_val),

      .covariance_val(covariance_val),

      .eigen1(eigen1),
      .eigen2(eigen2),

      .calc_finished_pulse(calc_finished_pulse)
  );

  //----------------------
  // Clock Generator
  //----------------------
  always #5 clk = ~clk;   // 100 MHz

  //----------------------
  // Debug Monitor
  //----------------------
  initial begin
    $monitor("TIME=%0t | P1=%d P2=%d | R1=%d R2=%d | COV=%d | E1=%d E2=%d | DONE=%b",
              $time,
              current_price_s1,
              current_price_s2,
              s1_return_val,
              s2_return_val,
              covariance_val,
              eigen1,
              eigen2,
              calc_finished_pulse);
  end

  //----------------------
  // Stimulus
  //----------------------
  initial begin

    clk = 0;
    rst_n = 0;
    uart_rx_line = 1'b1;

    // reset
    #50;
    rst_n = 1;

    // run simulation
    #1000000;

    $stop;
  end

endmodule