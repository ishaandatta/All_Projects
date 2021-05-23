///-------------------------------------------------------------------------
//    Ball.sv                                                            --
//    Viral Mehta                                                        --
//    Spring 2005                                                        --
//                                                                       --
//    Modified by Stephen Kempf 03-01-2006                               --
//                              03-12-2007                               --
//    Translated by Joe Meng    07-07-2013                               --
//    Modified by Po-Han Huang  12-08-2017                               --
//    Spring 2018 Distribution                                           --
//                                                                       --
//    For use with ECE 385 Lab 8                                         --
//    UIUC ECE Department                                                --
//-------------------------------------------------------------------------


module  ball ( input         Clk,                // 50 MHz clock
                             Reset,              // Active-high reset signal
                             frame_clk,          // The clock indicating a new frame (~60Hz)
               input [7:0]	 keycode,			 // keyboard input
               input [9:0]   DrawX, DrawY,       // Current pixel coordinates
               output logic  is_ball,             // Whether current pixel belongs to ball or background
			   /* New code for ball breaker*/
			   output logic  is_brick,			 //Current pixel is brick?
			   output logic  is_paddle				// Current pixel is paddle?
			  
			    /* New code for ball breaker ends*/
              );
    
    parameter [9:0] Ball_X_Center = 10'd320;  // Center position on the X axis
    parameter [9:0] Ball_Y_Center = 10'd240;  // Center position on the Y axis
    parameter [9:0] Ball_X_Min = 10'd0;       // Leftmost point on the X axis
    parameter [9:0] Ball_X_Max = 10'd639;     // Rightmost point on the X axis
    parameter [9:0] Ball_Y_Min = 10'd0;       // Topmost point on the Y axis
    parameter [9:0] Ball_Y_Max = 10'd479;     // Bottommost point on the Y axis
    parameter [9:0] Ball_X_Step = 10'd1;      // Step size on the X axis
    parameter [9:0] Ball_Y_Step = 10'd1;      // Step size on the Y axis
    parameter [9:0] Ball_Size = 10'd4;        // Ball size
	 
	
	/* New code for ball breaker*/

	 parameter [9:0] Paddle_Xtop = 10'd280;  // Paddle top left Corner X coordinate
    parameter [9:0] Paddle_Ytop = 10'd465;  // Paddle top left Corner Y coordinate
	 parameter [9:0] Paddle_Xbottom = 10'd360;  // Paddle bottom right Corner X coordinate
    parameter [9:0] Paddle_Ybottom = 10'd470;  // Paddle bottom right Corner Y coordinate
	 parameter [9:0] Paddle_width = 10'd80;  // Width of Paddle
    parameter [9:0] Paddle_height = 10'd5;  // Height of Paddle
	 parameter [9:0] Paddle_X_Max = 10'd559; // 639-80 =one paddle length less than right wall 
	 
	 parameter [9:0] Paddle_X_Step = 10'd10; //May need to increase this if our paddle moves too slow
	 
	 
	 parameter [9:0] Brick_width = 10'd100;  // Width of brick
    parameter [9:0] Brick_height = 10'd20;  // Height of brick
    parameter [9:0] Brick_gapX = 10'd4;       // Gap between adjacent bricks - x axis
    parameter [9:0] Brick_gapY = 10'd2;     // Gap between adjacent bricks - y axis
    parameter [9:0] Bricks_num = 10'd12;      // Number of bricks
	
    parameter [9:0] Brick_top_x = 10'd110;      // Top left brick - x coordinate
    parameter [9:0] Brick_top_y = 10'd10;      // Top left brick - y coordinate
	 parameter [9:0] Brick_cols = 10'd4;      // Bricks in each row
    parameter [9:0] Brick_rows = 10'd3;      // Number of rows of bricks
	 

		 
	 /* New code for ball breaker ends*/
    logic [9:0] Paddle_X_Pos,Paddle_Xbottomr_Pos, Paddle_Ytopl_Pos,Paddle_Ybottomr_Pos; //Modify only in always_ff
	logic [9:0] Paddle_X_Pos_in,Paddle_cur_y1, Paddle_cur_x2,Paddle_cur_y2,Paddle_Motion, Paddle_Motion_in; //Modify only in always comb
    logic [9:0] Ball_X_Pos, Ball_X_Motion, Ball_Y_Pos, Ball_Y_Motion;
    logic [9:0] Ball_X_Pos_in, Ball_X_Motion_in, Ball_Y_Pos_in, Ball_Y_Motion_in;

    //logic [7:0] W = 8'h1A;
    logic [7:0] A = 8'h04;
    //logic [7:0] S = 8'h16;
    logic [7:0] D = 8'h07;
	 

	/* New code for ball breaker*/
	typedef struct packed {
		logic [9:0] x1; //Top left X
		logic [9:0] y1; //Top left Y
		logic [9:0] x2; //Bottom right X
		logic [9:0] y2; //Bottom right Y
		logic visible;
		} brick;
		
	brick bricks[Brick_rows][Brick_cols];
	brick cur_bricks[Brick_rows][Brick_cols];
	

	
    
    //////// Do not modify the always_ff blocks. ////////
    // Detect rising edge of frame_clk
    logic frame_clk_delayed, frame_clk_rising_edge;
    always_ff @ (posedge Clk) begin
        frame_clk_delayed <= frame_clk;
        frame_clk_rising_edge <= (frame_clk == 1'b1) && (frame_clk_delayed == 1'b0);
    end
    // Update registers
    always_ff @ (posedge Clk) begin
	
		byte i;
		byte j;
        if (Reset)
        begin
            Ball_X_Pos <= Ball_X_Center;
            Ball_Y_Pos <= Ball_Y_Center;
            Ball_X_Motion <= Ball_X_Step;            /* New Code in Ball breaker : Original was "Ball_X_Motion <= 10'd0;" */
            Ball_Y_Motion <= Ball_Y_Step;
				
				
			/* New code for ball breaker*/
			
								
			Paddle_X_Pos<=Paddle_Xtop ;
			Paddle_Xbottomr_Pos<=Paddle_Xbottom;
			Paddle_Ytopl_Pos<=Paddle_Ytop;
			Paddle_Ybottomr_Pos<=Paddle_Ybottom;
			
			Paddle_Motion <= 10'd0;
//			Paddle_X_Pos_in <= Paddle_Xtop;
//			Paddle_cur_x2 <= Paddle_Xbottom;
			
		
								
			/* New code for ball breaker ends*/
			
        end
        else
        begin
            Ball_X_Pos <= Ball_X_Pos_in;
            Ball_Y_Pos <= Ball_Y_Pos_in;
            Ball_X_Motion <= Ball_X_Motion_in;
            Ball_Y_Motion <= Ball_Y_Motion_in;
			/* New code for ball breaker*/	
			Paddle_X_Pos<=Paddle_X_Pos_in ;
			Paddle_Xbottomr_Pos<=Paddle_cur_x2;
			Paddle_Ytopl_Pos<=Paddle_cur_y1;
			Paddle_Ybottomr_Pos<=Paddle_cur_y2;
			Paddle_Motion <= Paddle_Motion_in;
//
//			for (i=0;i<Brick_rows;i++) begin
//					for (j=0;j<Brick_cols;j++) begin
////							bricks[i][j].x1<= cur_bricks[i][j].x1;
////							bricks[i][j].y1<= cur_bricks[i][j].y1;
////							bricks[i][j].x2<= cur_bricks[i][j].x2;
////							bricks[i][j].y2<= cur_bricks[i][j].y2;
////							bricks[i][j].visible<=cur_bricks[i][j].visible;
//						end
//				end
			
			/* New code for ball breaker ends*/
				
        end
    end
    //////// Do not modify the always_ff blocks. ////////
    
    // You need to modify always_comb block.
    always_comb begin
	 	int i;
		int j;
        // By default, keep motion and position of ball unchanged
        Ball_X_Pos_in = Ball_X_Pos;
        Ball_Y_Pos_in = Ball_Y_Pos;
        Ball_X_Motion_in = Ball_X_Motion;
        Ball_Y_Motion_in = Ball_Y_Motion;
		 // By default, keep position of paddle unchanged, the paddle does not have to be
		 // continuously moving
		Paddle_X_Pos_in = Paddle_X_Pos ;
		Paddle_cur_x2 = Paddle_Xbottomr_Pos;
		Paddle_Motion_in = Paddle_Motion;
		//		Paddle_step	  = 10'd0;  -- SWITCH TO OLD MOTION HANDLING (Paddle_step)
		Paddle_cur_y1 = Paddle_Ytopl_Pos;
		Paddle_cur_y2 = Paddle_Ybottomr_Pos;
//		Paddle_Motion = 10'd0;
		for (i=0;i<Brick_rows;i++)
			begin 
				for (j=0;j<Brick_cols;j++)
					begin
						cur_bricks[i][j].x1= bricks[i][j].x1;
						cur_bricks[i][j].y1= bricks[i][j].y1;
						cur_bricks[i][j].x2= bricks[i][j].x2;
						cur_bricks[i][j].y2= bricks[i][j].y2;
						cur_bricks[i][j].visible=bricks[i][j].visible;
					end
			end
		
        // Update position and motion of everything only at rising edge of frame clock
        if (frame_clk_rising_edge)
        begin
			for (i=0;i<Brick_rows;i++)
				begin
					for (j=0;j<Brick_cols;j++)
						begin
							if(bricks[i][j].visible==1'b1);
								begin
									if(((Ball_X_Pos + Ball_Size) >= bricks[i][j].x1) && ((Ball_X_Pos + Ball_Size) <= bricks[i][j].x2)
									&& ((Ball_Y_Pos + Ball_Size) >= bricks[i][j].y1) && ((Ball_Y_Pos + Ball_Size) <= bricks[i][j].y2))
										begin
											cur_bricks[i][j].visible=1'b0; // Ball touched it...Break the brick... i.e make it invisible
											// Also make the ball bounce off the brick
											if( Ball_Y_Pos + Ball_Size <= bricks[i][j].y2 )  // Ball is at the bottom edge, BOUNCE DOWN!
												Ball_Y_Motion_in = Ball_Y_Step;  // 2's complement.  
											else if ( Ball_Y_Pos + Ball_Size >= bricks[i][j].y1 )  // Ball is at the top edge, BOUNCE UP!
												Ball_Y_Motion_in = (~(Ball_Y_Step) + 1'b1);
											if( Ball_X_Pos + Ball_Size <= bricks[i][j].x2 )  // Ball is at the right edge, BOUNCE R!
												Ball_X_Motion_in = Ball_X_Step;   // 2's complement.  
											else if ( Ball_X_Pos + Ball_Size  >= bricks[i][j].x1)  // Ball is at the left edge, Bounce L!
												Ball_X_Motion_in = (~(Ball_X_Step) + 1'b1);
										end	
								end
						end
				end
			
				/* old code for ball */
            // Be careful when using comparators with "logic" datatype because compiler treats 
            //   both sides of the operator as UNSIGNED numbers.
            // e.g. Ball_Y_Pos - Ball_Size <= Ball_Y_Min 
            // If Ball_Y_Pos is 0, then Ball_Y_Pos - Ball_Size will not be -4, but rather a large positive number.
            if( Ball_Y_Pos + Ball_Size >= Ball_Y_Max )  // Ball is at the bottom edge, BOUNCE!
                Ball_Y_Motion_in = (~(Ball_Y_Step) + 1'b1);  // 2's complement.  
            else if ( Ball_Y_Pos <= Ball_Y_Min + Ball_Size )  // Ball is at the top edge, BOUNCE!
                Ball_Y_Motion_in = Ball_Y_Step;
            // TODO: Add other boundary detections and handle keypress here.
            if( Ball_X_Pos + Ball_Size >= Ball_X_Max )  // Ball is at the right edge, BOUNCE!
                Ball_X_Motion_in = (~(Ball_X_Step) + 1'b1);  // 2's complement.  
            else if ( Ball_X_Pos <= Ball_X_Min + Ball_Size )  // Ball is at the left edge, BOUNCE!
                Ball_X_Motion_in = Ball_X_Step;
				/* old code for ball ends*/
				
				//Bounce the ball off the Paddle if it touches it
				 if(( Ball_X_Pos + Ball_Size >= Paddle_X_Pos ) && ( Ball_X_Pos + Ball_Size <= Paddle_Xbottomr_Pos ) &&
					( Ball_Y_Pos + Ball_Size >= Paddle_Ytopl_Pos ) && ( Ball_Y_Pos + Ball_Size <= Paddle_Ybottomr_Pos ))
						Ball_Y_Motion_in = (~(Ball_Y_Step) + 1'b1);  // 2's complement. 	
						
			 
				//Keypress for Paddle left or right 'A is left, 'D' is right
				if(keycode == A) 
					begin //going left so Paddle_Motion should be -1
						Paddle_Motion_in  =	(~(Ball_X_Step) + 1'b1);
						if(Paddle_X_Pos >= Paddle_X_Step ) 
								Paddle_Motion_in = 10'd0;
								
								//OLD
//						if(Paddle_Xtopl_Pos >= Paddle_X_Step) //If left edge NOT reached.. change position
//						Paddle_step= (~(Paddle_X_Step) + 1'b1);
					end				
				if(keycode == D) 
					begin //Paddle going Right so Paddle_Motion should be +1
						Paddle_Motion_in  =		10'd1;
						if(Paddle_Xbottomr_Pos < Paddle_X_Max ) //If Right edge reached.. change position
								Paddle_Motion_in = (~(Ball_X_Step) + 1'b1); 
								
								//OLD
//						if(Paddle_Xtopl_Pos < Paddle_X_Max) //If Right edge NOT reached.. change position
//						Paddle_step=Paddle_X_Step; 
					end				
		//If left edge NOT reached.. change position
		
            // Update the ball and Paddle position with its motion
            Ball_X_Pos_in = Ball_X_Pos + Ball_X_Motion;
            Ball_Y_Pos_in = Ball_Y_Pos + Ball_Y_Motion;
				
			Paddle_X_Pos_in =  Paddle_Xtop + Paddle_X_Pos + Paddle_Motion; //Paddle_X_Pos_in 
			Paddle_cur_x2 =  Paddle_Xbottom + Paddle_Xbottomr_Pos + Paddle_Motion;
        end
//			Paddle_cur_x1 = Paddle_Xtop + Paddle_step;
//			Paddle_cur_x2 = Paddle_Xbottom + Paddle_step;
        
        /**************************************************************************************
            ATTENTION! Please answer the following quesiton in your lab report! Points will be allocated for the answers!
            Hidden Question #2/2:
               Notice that Ball_Y_Pos is updated using Ball_Y_Motion. 
              Will the new value of Ball_Y_Motion be used when Ball_Y_Pos is updated, or the old? 
              What is the difference between writing
                "Ball_Y_Pos_in = Ball_Y_Pos + Ball_Y_Motion;" and 
                "Ball_Y_Pos_in = Ball_Y_Pos + Ball_Y_Motion_in;"?
              How will this impact behavior of the ball during a bounce, and how might that interact with a response to a keypress?
              Give an answer in your Post-Lab.
        **************************************************************************************/
    end
    
    // Compute whether the pixel corresponds to ball or background
    /* Since the multiplicants are required to be signed, we have to first cast them
       from logic to int (signed by default) before they are multiplied. */
    int DistX, DistY, Size;
    assign DistX = DrawX - Ball_X_Pos;
    assign DistY = DrawY - Ball_Y_Pos;
    assign Size = Ball_Size;
	
    always_comb 
	 
	 begin
	 
			// Check if ball
			
			int i;
			int j;
			
        if ( ( DistX*DistX + DistY*DistY) <= (Size*Size) ) 
            is_ball = 1'b1;
        else
            is_ball = 1'b0;
        /* The ball's (pixelated) circle is generated using the standard circle formula.  Note that while 
           the single line is quite powerful descriptively, it causes the synthesis tool to use up three
           of the 12 available multipliers on the chip! */
			
			/* New code for ball breaker*/
			// Check if Brick
			
		  for (i=0;i<Brick_rows;i++)
				begin
					for (j=0;j<Brick_cols;j++)
						begin
							if(bricks[i][j].visible==1'b1);
								begin
									if((DrawX >= bricks[i][j].x1) && (DrawX <= bricks[i][j].x2)
									&& (DrawY >= bricks[i][j].y1) && (DrawY <= bricks[i][j].y2))
										is_brick=1'b1; 
									else
										is_brick=1'b0;
								end
						end
				end
				
			//Check if Paddle
			if((DrawX >= Paddle_X_Pos) && (DrawX <= Paddle_Xbottomr_Pos)
				&& (DrawY >= Paddle_Ytopl_Pos) && (DrawY <= Paddle_Ybottomr_Pos))
				is_paddle=1'b1;
			else
				is_paddle=1'b0;
				
			/* New code for ball breaker ends*/
			
    end
    
endmodule


