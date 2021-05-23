module datapath(
    input logic GatePC, GateMDR, GateALU, GateMARMUX,
	 input logic [15:0] PC, addadder, MDR, ALU_out,
//    input logic ADDR1MUX, SR1MUX, SR2MUX, MIO_EN, PCMUX, DRMUX, 
//					 ADDR2MUX, ALUK, LD_REG, LD_BEN, LD_CC, 
//					 LD_IR, LD_MAR, LD_MDR, LD_PC, LD_LED,
	 output logic [15:0] bus_out);

always_comb begin
	if(GatePC + GateMDR + GateALU + GateMARMUX > 2) //unnecessary
		bus_out = 16'b0000000000111100;  //EXCEPTION #60
	else begin
		unique case ({GatePC, GateMDR, GateMARMUX, GateALU})
			4'b1000 : bus_out = PC;
			4'b0100 : bus_out = MDR;
			4'b0010 : bus_out = addadder;
			4'b0001 : bus_out = ALU_out;
			default : bus_out = 1'bz; // ??
		endcase
	end
	end
endmodule
