module alu	(	input logic [1:0] ALUK,
					input logic [15:0] A, B,
					output logic [15:0] ALU_out
				);
				
	always_comb begin
		unique case (ALUK)
			2'b00 :	ALU_out = A & B;
			2'b01 :	ALU_out = ~A;
			2'b10 :	ALU_out = A + B;
			2'b11 :	ALU_out = A;
			default :	ALU_out = 16'bx;
			
		endcase
	end
endmodule