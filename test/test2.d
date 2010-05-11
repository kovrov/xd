void _main()
{
	auto connection = new Connection;  // open connection with the server
	auto scr = connection.screens[0];  // get the first screen
	Visual visual;
	depths_loop: foreach (d; &scr.allowed_depths)
	{
		foreach (vt; &d.visuals)
		{
			if (scr.root_visual == vt.visual_id)
			{
				visual = vt;
				break depths_loop;
			}
		}
	}

//xcb_window_t root = setup.roots[0];
//ubyte depth = setup.roots[0].root_depth;
//xcb_visualid_t visual = setup.roots[0].root_visual;

	auto window = new Window(connection, scr.root, -1,-1, 100, 100, 0, visual,
			[XCB_CW_BACK_PIXEL: scr.white_pixel,
			 XCB_CW_EVENT_MASK: XCB_EVENT_MASK_EXPOSURE | XCB_EVENT_MASK_KEY_PRESS]);

	auto gc = new GC(window, [XCB_GC_FOREGROUND: scr.black_pixel,
	                          XCB_GC_GRAPHICS_EXPOSURES: 0]);

	window.map();
	connection.flush();

	event_loop: while (true)
	{
		xcb_generic_event_t* e = connection.wait_for_event();
		scope (exit) free(e);

		switch (e.response_type & ~0x80)
		{
		case XCB_EXPOSE:  // draw or redraw the window
			auto exp_ev = cast(xcb_expose_event_t*)e;
			assert (exp_ev.window == cast(xcb_window_t)window);
			gc.poly_fill(xcb_rectangle_t(20, 20, 60, 60), 1);
			connection.flush();
			break;
		case XCB_KEY_PRESS:  // exit on key press
			break event_loop;
		}
	}
}
