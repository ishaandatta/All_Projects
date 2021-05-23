module PCMUX( input logic [15:0] in_1,in_2, in_3, 
								input logic [1:0] select, 
								output logic [15:0] mux_out
							);
							
always_comb begin
		
		unique case (select)
			2'b00 : mux_out = in_1;
			2'b01 : mux_out = in_2;
			2'b10 : mux_out = in_3;
			default : mux_out = 16'b0; // ??
		endcase
		
	end
endmodule
							
			
module mux_16bit_2to1 ( input logic [15:0] in_1,in_2, 
								input logic select, 
								output logic [15:0] mux_out
							);

	always_comb begin
		unique case (select)
			1'b0	:	mux_out = in_1;
			1'b1	:	mux_out = in_2;
			default :	mux_out = 16'bx;
		endcase
	end

endmodule


module mux_3bit_2to1(input logic [2:0] in_1,in_2, 
								input logic select, 
								output logic [2:0] mux_out);

	always_comb begin
		unique case (select)
			1'b0	:	mux_out = in_1;
			1'b1	:	mux_out = in_2;
			default :	mux_out = 3'bx;
		endcase
	end
	
endmodule


module mux_16bit_4to1 ( input logic [15:0] in_1,in_2, in_3, in_4, 
								input logic [1:0] select, 
								output logic [15:0] mux_out
							);

	always_comb begin
		unique case (select)
			2'b00 : mux_out = in_1;
			2'b01 : mux_out = in_2;
			2'b10 : mux_out = in_3;
			2'b11 : mux_out = in_4; // ??
			default :	mux_out = 16'bx;
		endcase
	end

endmodule