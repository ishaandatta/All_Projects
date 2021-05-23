//------------------------------------------------------------------------------
// Company:        UIUC ECE Dept.
// Engineer:       Stephen Kempf
//
// Create Date:    
// Design Name:    ECE 385 Lab 6 Given Code - SLC-3 
// Module Name:    SLC3
//
// Comments:
//    Revised 03-22-2007
//    Spring 2007 Distribution
//    Revised 07-26-2013
//    Spring 2015 Distribution
//    Revised 09-22-2015 
//    Revised 10-19-2017 
//    spring 2018 Distribution
//
//------------------------------------------------------------------------------
module slc3(
    input logic [15:0] S,
    input logic Clk, Reset, Run, Continue,
    output logic [11:0] LED,
    output logic [6:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5, HEX6, HEX7,
    output logic CE, UB, LB, OE, WE,
    output logic [19:0] ADDR,
    inout wire [15:0] Data //tristate buffers need to be of type wire
);

// Declaration of push button active high signals
logic Reset_ah, Continue_ah, Run_ah;

assign Reset_ah = ~Reset;
assign Continue_ah = ~Continue;
assign Run_ah = ~Run;

// Internal connections
logic BEN;
logic LD_MAR, LD_MDR, LD_IR, LD_BEN, LD_CC, LD_REG, LD_PC, LD_LED;
logic GatePC, GateMDR, GateALU, GateMARMUX;
logic [1:0] PCMUX_select, ADDR2MUX_select, ALUK;
logic DRMUX_select, SR1MUX_select, SR2MUX_select, ADDR1MUX_select;
logic MIO_EN; //MDR select

logic [15:0] MDR_In;
logic [15:0] MAR, MDR, IR, PC, ALU, addadder;
logic [15:0] Data_from_SRAM, Data_to_SRAM;

// Added Internal connections
logic [15:0] bus_out;

//REGISTER logic
logic N, Z, P, N_data_out, Z_data_out, P_data_out, BEN_data_out;
logic [15:0] SR1_out, SR2_out;
//MUX logic
logic [2:0] DRMUX_out, SR1MUX_out;
logic [15:0] ADDR1MUX_out, ADDR2MUX_out, SR2MUX_out;
	
//computation logic
logic [15:0] ALU_out; 
					
logic [15:0] Data_from_CPU, Data_to_CPU;
// Signals being displayed on hex display
logic [3:0][3:0] hex_4;


//For week 1, hexdrivers will display IR. Comment out these in week 2.
//HexDriver hex_driver3 (IR[15:12], HEX3);
//HexDriver hex_driver2 (IR[11:8], HEX2);
//HexDriver hex_driver1 (IR[7:4], HEX1);
//HexDriver hex_driver0 (IR[3:0], HEX0);

// For week 2, hexdrivers will be mounted to Mem2IO
 HexDriver hex_driver3 (hex_4[3][3:0], HEX3);
 HexDriver hex_driver2 (hex_4[2][3:0], HEX2);
 HexDriver hex_driver1 (hex_4[1][3:0], HEX1);
 HexDriver hex_driver0 (hex_4[0][3:0], HEX0);

// The other hex display will show PC for both weeks.
HexDriver hex_driver7 (PC[15:12], HEX7);
HexDriver hex_driver6 (PC[11:8], HEX6);
HexDriver hex_driver5 (PC[7:4], HEX5);
HexDriver hex_driver4 (PC[3:0], HEX4);

// Connect MAR to ADDR, which is also connected as an input into MEM2IO.
// MEM2IO will determine what gets put onto Data_CPU (which serves as a potential
// input into MDR)
assign ADDR = { 4'b00, MAR }; //Note, our external SRAM chip is 1Mx16, but address space is only 64Kx16
assign MIO_EN = ~OE;

assign addadder = ADDR1MUX_out + ADDR2MUX_out;

always_comb begin
N = bus_out[15];
if (bus_out == 16'b0)
	begin
	Z = 1'b1;
	end
else begin
	Z = 1'b0;
	end
P = ~bus_out[15] & ~Z;
BEN = (IR[11] & N_data_out) | (IR[10] & Z_data_out) | (IR[9] & P_data_out);
end


// You need to make your own datapath module and connect everything to the datapath
// Be careful about whether Reset is active high or low
datapath d0 (.*, .addadder(addadder));
//reg_unit reg_unit (.*);


PC_UNIT PC_unit (.Clk(Clk), .Reset(Reset), .LD_PC(LD_PC), .PCMUX_select(PCMUX_select),
					.bus_out(bus_out), .addrmux(addadder), .data_out(PC)); //done
//mux_16bit_3to1  PCMUX (.*, in_1(), in_2(), in_3(), select(PCMUX_select), mux_out(PCMUX_out)) //PCMUX_select? in_#s?

register_unit_8x16 REG_FILE (.*, .data_in(bus_out), .SR2(IR[2:0]));

reg_16bit MAR_reg (.*, .Load(LD_MAR), .data_in(bus_out), .data_out(MAR));
MDR_UNIT MDR_UNIT (.*, .MIO_EN(MIO_EN), .data_out(MDR));

reg_16bit IR_reg (.*, .data_in(bus_out), .Load(LD_IR), .data_out(IR));

reg_1_bit N_reg (.*, .Load(LD_CC), .data_in(N), .data_out(N_data_out));
reg_1_bit Z_reg (.*, .Load(LD_CC), .data_in(Z), .data_out(Z_data_out));
reg_1_bit P_reg ( .*, .Load(LD_CC), .data_in(P), .data_out(BEN_data_out));
reg_1_bit BEN_reg (.*, .Load(LD_BEN), .data_in(BEN), .data_out(BEN_data_out));


mux_3bit_2to1 DRMUX (
	 .in_1(3'b111), .in_2(IR[11:9]),
    .select(DRMUX_select),
    .mux_out(DRMUX_out)
);


mux_16bit_2to1 ADDR1MUX (
    .in_1(SR1_out), .in_2(PC),
    .select(ADDR1MUX_select),
    .mux_out(ADDR1MUX_out)
);


mux_16bit_4to1 ADDR2MUX (
	 .in_1( {{5{IR[10]}}, IR[10:0]} ), 
	 .in_2( {{7{IR[8]}}, IR[ 8:0]} ),
	 .in_3( { {10{IR[5]}}, IR[ 5:0]} ),
    .in_4(16'b0),
	 .select(ADDR2MUX_select),
	 .mux_out(ADDR2MUX_out)
);


mux_3bit_2to1 SR1MUX (
    .in_1(IR[11:9]), .in_2(IR[8:6]),
    .select(SR1MUX_select),
    .mux_out(SR1MUX_out)
);


mux_16bit_2to1 SR2MUX (
    .in_1({{11{IR[4]}}, IR[4:0]}), .in_2(SR2_out),
    .select(SR2MUX_select),
    .mux_out(SR2MUX_out)
);




//Our SRAM and I/O controller
Mem2IO memory_subsystem(
    .*, .Reset(Reset_ah), .ADDR(ADDR), .Switches(S),
    .HEX0(hex_4[0][3:0]), .HEX1(hex_4[1][3:0]), .HEX2(hex_4[2][3:0]), .HEX3(hex_4[3][3:0]),
    .Data_from_CPU(MDR), .Data_to_CPU(MDR_In),
    .Data_from_SRAM(Data_from_SRAM), .Data_to_SRAM(Data_to_SRAM)
);

//The tri-state buffer serves as the interface between Mem2IO and SRAM
tristate #(.N(16)) tr0(
    .Clk(Clk), .tristate_output_enable(~WE), .Data_write(Data_to_SRAM), .Data_read(Data_from_SRAM), .Data(Data)
);



// State machine and control signals
ISDU state_controller(
    .*, .Reset(Reset_ah), .Run(Run_ah), .Continue(Continue_ah),
    .Opcode(IR[15:12]), .IR_5(IR[5]), .IR_11(IR[11]),
    .Mem_CE(CE), .Mem_UB(UB), .Mem_LB(LB), .Mem_OE(OE), .Mem_WE(WE)
);



// COMPUTATION
alu ALU_core (
    .ALUK(ALUK),
    .A(SR1_out), .B(SR2MUX_out),
    .ALU_out(ALU_out)
);

//alu adder (
//    .select(2'b10),
//    .A_in(ADDR1MUX_out), .B_in(ADDR2MUX_out),
//    .out(ALU_ADDER_OUT)
//);

endmodule
