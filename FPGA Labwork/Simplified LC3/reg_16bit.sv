module reg_16bit (input  logic Clk, Reset, Load,
						input logic [15:0] data_in,
						output logic [15:0] data_out
						);
						
	always_ff @ (posedge Clk)
    begin
	 	 if (~Reset) //notice, this is a sycnrhonous reset, which is recommended on the FPGA
			  data_out <= 16'h00;
		 else if (Load)
			  data_out <= data_in;
	 end
	 
endmodule
	 
	

 module reg_1_bit (
    input  logic Clk, Reset, Load,
    input  logic data_in,
    output logic data_out
);

	always_ff @ (posedge Clk)
	 begin
		 if (~Reset) //notice, this is a sycnrhonous reset, which is recommended on the FPGA
			  data_out <= 1'h0;
		 else if (Load)
			  data_out <= data_in;
	 end
endmodule

	
 
//module reg_unit (input  logic Clk, Reset, LD_REG,
//					input logic [2:0] SR1_MUX, DRMUX, SR2, 
//					input logic [15:0] data_in,
//					output logic [15:0] SR1_OUT, SR2_OUT
//					);
//					
//
//	always_comb
//		begin
//			
//			
//			
//		end
// 
//endmodule

//input logic 	CLK, LD_REG, reset,
//				input logic		[15:0] 	data_in,
//				input logic 	[2:0]	DRMUX_out, SR1, SR2,
//				output logic 	[15:0]	SR1_OUT, SR2_OUT
 
module register_unit_8x16 ( input  logic Clk, Reset, LD_REG,
								input logic [2:0]   DRMUX_out, SR1MUX_out,SR2,
								input  logic [15:0] data_in,
								output logic [15:0] SR1_out, SR2_out
);


logic [15:0] reg0_val, reg1_val, reg2_val, reg3_val, reg4_val, reg5_val, reg6_val, reg7_val;

logic reg0_Load, reg1_Load, reg2_Load, reg3_Load, reg4_Load, reg5_Load, reg6_Load, reg7_Load, test_del;

reg_16bit reg0(.*, .Load(reg0_Load),
						.data_in(data_in),
						.data_out(reg0_val)
						);

reg_16bit reg1(.*, .Load(reg1_Load),
						.data_in(data_in),
						.data_out(reg1_val)
						);

reg_16bit reg2(.*, .Load(reg2_Load),
						.data_in(data_in),
						.data_out(reg2_val)
						);

reg_16bit reg3(.*, .Load(reg3_Load),
						.data_in(data_in),
						.data_out(reg3_val)
						);

reg_16bit reg4(.*, .Load(reg4_Load),
						.data_in(data_in),
						.data_out(reg4_val)
						);

reg_16bit reg5(.*, .Load(reg5_Load),
						.data_in(data_in),
						.data_out(reg5_val)
						);

reg_16bit reg6(.*, .Load(reg6_Load),
						.data_in(data_in),
						.data_out(reg6_val)
						);

reg_16bit reg7(.*, .Load(reg7_Load),
						.data_in(data_in),
						.data_out(reg7_val)
						);
						
	always_comb
	begin
	
		reg0_Load = 1'b0;
		reg1_Load = 1'b0;
		reg2_Load = 1'b0;
		reg3_Load = 1'b0;
		reg4_Load = 1'b0;
		reg5_Load = 1'b0;
		reg6_Load = 1'b0;
		reg7_Load = 1'b0;
	
	if(LD_REG)
	begin
		unique case(DRMUX_out)
		3'b000 : reg0_Load = 1'b1;
		3'b001 : reg1_Load = 1'b1;
		3'b010 : reg2_Load = 1'b1;
		3'b011 : reg3_Load = 1'b1;
		3'b100 : reg4_Load = 1'b1;
		3'b101 : reg5_Load = 1'b1;
		3'b110 : reg6_Load = 1'b1;
		3'b111 : reg7_Load = 1'b1;
		//default : test_del = 1'b0;
		endcase
		end
//		else
//		begin
//			reg0_Load = 1'b0;
//			reg1_Load = 1'b0;
//			reg2_Load = 1'b0;
//			reg3_Load = 1'b0;
//			reg4_Load = 1'b0;
//			reg5_Load = 1'b0;
//			reg6_Load = 1'b0;
//			reg7_Load = 1'b0;
//		end
		
	//else
	//begin
		
	//end
	end
	

	always_comb
	begin
		unique case(SR1MUX_out)
		3'b000 : SR1_out = reg0_val;
		3'b001 : SR1_out = reg1_val;
		3'b010 : SR1_out = reg2_val;
		3'b011 : SR1_out = reg3_val;
		3'b100 : SR1_out = reg4_val;
		3'b101 : SR1_out = reg5_val;
		3'b110 : SR1_out = reg6_val;
		3'b111 : SR1_out = reg7_val;
		//default : test_del <= 1'b0;
	endcase
	
		unique case(SR2)
		3'b000 : SR2_out = reg0_val;
		3'b001 : SR2_out = reg1_val;
		3'b010 : SR2_out = reg2_val;
		3'b011 : SR2_out = reg3_val;
		3'b100 : SR2_out = reg4_val;
		3'b101 : SR2_out = reg5_val;
		3'b110 : SR2_out = reg6_val;
		3'b111 : SR2_out = reg7_val;
		//default : ;
		//default : test_del <= 1'b0;
	endcase
end


endmodule


