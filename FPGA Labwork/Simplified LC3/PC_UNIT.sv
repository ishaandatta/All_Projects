module PC_UNIT (input  logic Clk, Reset, LD_PC,
						input logic [1:0]PCMUX_select,
						input logic [15:0] bus_out, addrmux,
						output logic [15:0] data_out
						);
					
	logic [15:0] PC_out, PCMUX_out;
	
//	assign PC_out = PC_out + 1;
//	PCMUX  PCMUX (.*, .in_1(PC_out_incr), .in_2(bus_out), .in_3(16'bx), //addrmux 
//								.select(PCMUX_select), .mux_out(PCMUX_out)); //PCMUX_select? in_#s?
//	
	PCMUX  PCMUX (.*, .in_1(PC_out + 1'b1), .in_2(bus_out), .in_3(addrmux), 
								.select(PCMUX_select), .mux_out(PCMUX_out)); //PCMUX_select? in_#s?
	
	reg_16bit PC (.*, .Load(LD_PC), .data_in(PCMUX_out), .data_out(PC_out));
	
	assign data_out = PC_out;
//	always_comb begin
//		data_out = PC_out;
//		PC_out_incr = PC_out + 1;
//	end
	 
endmodule

 
 module MDR_UNIT (input  logic Clk, Reset, LD_MDR, MIO_EN,
						input logic [15:0] bus_out, MDR_In,
						output logic [15:0] data_out
						);
					
	logic [15:0] MDR_out, MDRMUX_out;
	
//	assign PC_out = PC_out + 1;
	
	mux_16bit_2to1  MDRMUX (.*, .in_1(bus_out), .in_2(MDR_In), 
								.select(MIO_EN), .mux_out(MDRMUX_out)); 
	
	reg_16bit MDR (.*, .Load(LD_MDR), .data_in(MDRMUX_out), .data_out(data_out));	
	 
endmodule
 