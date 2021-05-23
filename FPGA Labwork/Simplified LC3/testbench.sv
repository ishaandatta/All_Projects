module testbench();

timeunit 10ns;	// Half clock cycle at 50 MHz
			// This is the amount of time represented by #1 
timeprecision 1ns;

// These signals are internal because the processor will be 
// instantiated as a submodule in testbench.

logic Clk = 0;
logic Reset, Run, Continue, CE, UB, LB, OE, WE;
logic [15:0] S;
logic [19:0] ADDR;
wire [15:0] Data;
logic [11:0] LED;
logic [6:0] HEX0, HEX1, HEX2, HEX3, HEX4, HEX5, HEX6, HEX7; 

// To store expected results
logic [7:0] ans_1a, ans_2b;
				
// A counter to count the instances where simulation results
// do no match with expected results
integer ErrorCnt = 0;
		
// Instantiating the DUT
// Make sure the module and signal names match with those in your design
lab6_toplevel processor0(.*);	

// Toggle the clock
// #1 means wait for a delay of 1 timeunit
always begin : CLOCK_GENERATION
#1 Clk = ~Clk;
end

initial begin: CLOCK_INITIALIZATION
    Clk = 0;
end 

// Testing begins here
// The initial block is not synthesizable
// Everything happens sequentially inside an initial block
// as in a software program
initial begin: TEST_VECTORS
Reset = 0;
#2 Reset = 1;// Toggle Rest
Run = 1;
Continue = 1;

S = 16'h03; //Switches = HEX for Basic I/O Test

//#20 S = 16'h0B;		//Self-Modifying Code Test 
//#20 S = 16'h0B;		//Self-Modifying Code Test 

//S = 16'h33;	// Specify S



#20  Run = 0;	// Toggle A
#20  Run = 1;	// Toggle A
//#20  Continue = 0;
//#20  Run = 1;
//#5 Continue = 0;	// Toggle B
//#20 Continue = 1;


//#20 Run = 0;	// Toggle Execute
//#2 Run = 1;
//
//#22 Run = 0;
//    // Aval is expected to stay the same
//    // Bval is expected to be the answer of 1st cycle XNOR 8’h55
//    if (Aval != ans_1a)	
//	 ErrorCnt++;
//    ans_2b = ~(ans_1a ^ 8'h55); // Expected result of 2nd  cycle
//    if (Bval != ans_2b)
//	 ErrorCnt++;
//    R = 2'b11;
//#2 Run = 1;
//
//// Aval and Bval are expected to swap
//#22 if (Aval != ans_2b)
//	 ErrorCnt++;
//    if (Bval != ans_1a)
//	 ErrorCnt++;
//

if (ErrorCnt == 0)
	$display("Success!");  // Command line output in ModelSim
else
	$display("%d error(s) detected. Try again!", ErrorCnt);
end
endmodule