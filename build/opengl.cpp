// OpenGL linking.

#include <string.h>
#include "opengl.h"

#ifdef WIN32
// This malloc.h include is before SDL.h so that alloca will already be defined.
// Otherwise, SDL.h tries to include alloca.h, and fails.
# include <malloc.h>
# include <SDL.h>
#else
# include <SDL/SDL.h>
#endif

#include <GL/gl.h>
#include <GL/glu.h>

// On Windows we may need to patch up these missing definitions.
#ifdef WIN32
# ifndef GL_BGR
#  define GL_BGR  0x80E0
# endif
# ifndef GL_BGRA
#  define GL_BGRA 0x80E1
# endif
#endif


SDL_Surface* screen;
int mouse_x, mouse_y;

extern int screen_width, screen_height;
int screen_width, screen_height;

/*
v8::Handle<v8::Value> opengl_init(const v8::Arguments& x) {
	if (SDL_Init(SDL_INIT_VIDEO) < 0)
		return v8::Integer::New(1);
	return v8::Integer::New(0);
}
*/

v8::Handle<v8::Value> opengl_launch(const v8::Arguments& x) {
//	static int have_already_inited_glut = 0;
//	if (!have_already_inited_glut) {
//		int zero = 0;
//		glutInit(&zero, NULL);
//		have_already_inited_glut = 1;
//	}

	if (SDL_Init(SDL_INIT_VIDEO) < 0)
		return v8::Integer::New(1);

	const SDL_VideoInfo* info = SDL_GetVideoInfo();
	if (info == NULL) {
		printf("Unable to get video info: %s\n", SDL_GetError());
		return v8::Integer::New(1);
	}
	screen_width  = x[0]->Int32Value();
	screen_height = x[1]->Int32Value();

	int videoFlags = 0;
	videoFlags  = SDL_OPENGL;		  /* Enable OpenGL in SDL */
	videoFlags |= SDL_GL_DOUBLEBUFFER; /* Enable double buffering */
	videoFlags |= SDL_HWPALETTE;	   /* Store the palette in hardware */

	bool locked_framerate = true;

	int length = x.Length();	
	for (int ii=2; ii<length; ii++) {
		v8::String::AsciiValue arg(x[ii]);
		if (strcmp(*arg, "fullscreen") == 0) {
			videoFlags |= SDL_FULLSCREEN;
		} else if (strcmp(*arg, "resizable") == 0) {
			videoFlags |= SDL_RESIZABLE;
		} else if (strcmp(*arg, "maximize") == 0) {
			screen_width  = info->current_w;
			screen_height = info->current_h;
		} else if (strcmp(*arg, "unlocked-framerate") == 0) {
			locked_framerate = false;
		} else {
			cerr << "Unknown argument to opengl.launch: " << *arg << endl;
		}
	}

	if (info->blit_hw)
		videoFlags |= SDL_HWACCEL;

	if (locked_framerate)
		SDL_GL_SetAttribute(SDL_GL_SWAP_CONTROL, 1);

	if (!(screen = SDL_SetVideoMode(screen_width, screen_height, 32, videoFlags))) {
		SDL_Quit();
		return v8::Integer::New(1);
	}

//	SDL_ShowCursor(SDL_DISABLE);

	//glClearColor(0.2, 0.2, 0.8, 1.0);
	glClearColor(0.0, 0.0, 0.0, 1.0);

	glShadeModel(GL_SMOOTH);
	glEnable(GL_CULL_FACE);
	// Enables Depth Testing
	glEnable(GL_DEPTH_TEST);
	glEnable(GL_COLOR_MATERIAL);
	glClearStencil(0);
	// Enables Clearing Of The Depth Buffer
	glClearDepth(1.0);
	// The Type Of Depth Test To Do
	glDepthFunc(GL_LESS);
	glEnable(GL_BLEND);
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

	glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST);

	// Enable texture mapping
	glEnable(GL_TEXTURE_2D);

	glMatrixMode(GL_PROJECTION);

	// Reset The Projection Matrix
	glLoadIdentity();

	// Calculate The Aspect Ratio Of The Window
	gluPerspective(60.0f, screen_width / (double)screen_height, 0.05f, 4000.0f);

	glMatrixMode(GL_MODELVIEW);

	// Set up light 1
	glEnable(GL_LIGHTING);

	glLightModeli(GL_LIGHT_MODEL_LOCAL_VIEWER, GL_TRUE);

	GLfloat lmodel_ambient[] = { 0.2, 0.2, 0.2, 1.0 };
	glLightModelfv(GL_LIGHT_MODEL_AMBIENT, lmodel_ambient);

	glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE);
	glEnable(GL_COLOR_MATERIAL);

	GLfloat LightAmbient[]  = { 0.2f, 0.2f, 0.2f, 1.0f };
	GLfloat LightDiffuse[]  = { 0.7f, 0.7f, 0.7f, 1.0f };
	GLfloat LightPosition[] = { 0.0f, 0.0f, 0.0f, 1.0f };

	glLightfv(GL_LIGHT0, GL_AMBIENT,  LightAmbient);  // Add lighting -- Ambient
	glLightfv(GL_LIGHT0, GL_DIFFUSE,  LightDiffuse);  // Add lighting -- Diffuse
	glLightfv(GL_LIGHT0, GL_POSITION, LightPosition); // Set light position
	glEnable(GL_LIGHT0);

	return v8::Integer::New(0);
}

v8::Handle<v8::Value> opengl_quit(const v8::Arguments& x) {
	SDL_Quit();
	return v8::Integer::New(0);
}

v8::Handle<v8::Value> opengl_option(const v8::Arguments& x) {
	v8::String::AsciiValue arg(x[0]);
	if (strcmp(*arg, "cursor-visible") == 0) {
		if (x[1]->Int32Value()) SDL_ShowCursor(SDL_ENABLE);
		else SDL_ShowCursor(SDL_DISABLE);
	} else {
		cerr << "Unknown argument to opengl.option: " << *arg << endl;
		return v8::Integer::New(1);
	}
	return v8::Integer::New(0);
}

const char* key_translate(SDLKey x) {
	switch (x) {
		case SDLK_BACKSPACE: return "backspace"; case SDLK_TAB: return "tab"; case SDLK_CLEAR: return "clear";
		case SDLK_RETURN: return "return"; case SDLK_PAUSE: return "pause"; case SDLK_ESCAPE: return "escape";
		case SDLK_SPACE: return "space"; case SDLK_EXCLAIM: return "exclaim"; case SDLK_QUOTEDBL: return "quotedbl";
		case SDLK_HASH: return "hash"; case SDLK_DOLLAR: return "dollar"; case SDLK_AMPERSAND: return "ampersand";
		case SDLK_QUOTE: return "quote"; case SDLK_LEFTPAREN: return "left-parenthesis"; case SDLK_RIGHTPAREN: return "right-parenthesis";
		case SDLK_ASTERISK: return "asterisk"; case SDLK_PLUS: return "plus-sign"; case SDLK_COMMA: return "comma";
		case SDLK_MINUS: return "minus-sign"; case SDLK_PERIOD: return "period"; case SDLK_SLASH: return "forward-slash";
		case SDLK_0: return "0"; case SDLK_1: return "1"; case SDLK_2: return "2";
		case SDLK_3: return "3"; case SDLK_4: return "4"; case SDLK_5: return "5";
		case SDLK_6: return "6"; case SDLK_7: return "7"; case SDLK_8: return "8";
		case SDLK_9: return "9"; case SDLK_COLON: return "colon"; case SDLK_SEMICOLON: return "semicolon";
		case SDLK_LESS: return "less-than-sign"; case SDLK_EQUALS: return "equals-sign"; case SDLK_GREATER: return "greater-than-sign";
		case SDLK_QUESTION: return "question-mark"; case SDLK_AT: return "at"; case SDLK_LEFTBRACKET: return "left-bracket";
		case SDLK_BACKSLASH: return "backslash"; case SDLK_RIGHTBRACKET: return "right-bracket"; case SDLK_CARET: return "caret";
		case SDLK_UNDERSCORE: return "underscore"; case SDLK_BACKQUOTE: return "grave"; case SDLK_a: return "a";
		case SDLK_b: return "b"; case SDLK_c: return "c"; case SDLK_d: return "d";
		case SDLK_e: return "e"; case SDLK_f: return "f"; case SDLK_g: return "g";
		case SDLK_h: return "h"; case SDLK_i: return "i"; case SDLK_j: return "j";
		case SDLK_k: return "k"; case SDLK_l: return "l"; case SDLK_m: return "m";
		case SDLK_n: return "n"; case SDLK_o: return "o"; case SDLK_p: return "p";
		case SDLK_q: return "q"; case SDLK_r: return "r"; case SDLK_s: return "s";
		case SDLK_t: return "t"; case SDLK_u: return "u"; case SDLK_v: return "v";
		case SDLK_w: return "w"; case SDLK_x: return "x"; case SDLK_y: return "y";
		case SDLK_z: return "z"; case SDLK_DELETE: return "delete"; case SDLK_KP0: return "keypad-0";
		case SDLK_KP1: return "keypad-1"; case SDLK_KP2: return "keypad-2"; case SDLK_KP3: return "keypad-3";
		case SDLK_KP4: return "keypad-4"; case SDLK_KP5: return "keypad-5"; case SDLK_KP6: return "keypad-6";
		case SDLK_KP7: return "keypad-7"; case SDLK_KP8: return "keypad-8"; case SDLK_KP9: return "keypad-9";
		case SDLK_KP_PERIOD: return "keypad-period"; case SDLK_KP_DIVIDE: return "keypad-divide"; case SDLK_KP_MULTIPLY: return "keypad-multiply";
		case SDLK_KP_MINUS: return "keypad-minus"; case SDLK_KP_PLUS: return "keypad-plus"; case SDLK_KP_ENTER: return "keypad-enter";
		case SDLK_KP_EQUALS: return "keypad-equals"; case SDLK_UP: return "up-arrow"; case SDLK_DOWN: return "down-arrow";
		case SDLK_RIGHT: return "right-arrow"; case SDLK_LEFT: return "left-arrow"; case SDLK_INSERT: return "insert";
		case SDLK_HOME: return "home"; case SDLK_END: return "end"; case SDLK_PAGEUP: return "page-up";
		case SDLK_PAGEDOWN: return "page-down"; case SDLK_F1: return "F1"; case SDLK_F2: return "F2";
		case SDLK_F3: return "F3"; case SDLK_F4: return "F4"; case SDLK_F5: return "F5";
		case SDLK_F6: return "F6"; case SDLK_F7: return "F7"; case SDLK_F8: return "F8";
		case SDLK_F9: return "F9"; case SDLK_F10: return "F10"; case SDLK_F11: return "F11";
		case SDLK_F12: return "F12"; case SDLK_F13: return "F13"; case SDLK_F14: return "F14";
		case SDLK_F15: return "F15"; case SDLK_NUMLOCK: return "numlock"; case SDLK_CAPSLOCK: return "capslock";
		case SDLK_SCROLLOCK: return "scrollock"; case SDLK_RSHIFT: return "right-shift"; case SDLK_LSHIFT: return "left-shift";
		case SDLK_RCTRL: return "right-ctrl"; case SDLK_LCTRL: return "left-ctrl"; case SDLK_RALT: return "right-alt";
		case SDLK_LALT: return "left-alt"; case SDLK_RMETA: return "right-meta"; case SDLK_LMETA: return "left-meta";
		case SDLK_LSUPER: return "left-windows-key"; case SDLK_RSUPER: return "right-windows-key"; case SDLK_MODE: return "mode-shift";
		case SDLK_HELP: return "help"; case SDLK_PRINT: return "print-screen"; case SDLK_SYSREQ: return "SysRq";
		case SDLK_BREAK: return "break"; case SDLK_MENU: return "menu"; case SDLK_POWER: return "power";
		case SDLK_EURO: return "euro"; 	default: return "unknown";
	}
}

v8::Handle<v8::Value> opengl_poll(const v8::Arguments& x) {
	SDL_Event ev;
	if (SDL_PollEvent(&ev)) {
		v8::Handle<v8::Object> s = v8::Object::New();
		switch (ev.type) {
			case SDL_QUIT:
				s->Set(v8::String::New("RTSC_type"), v8::String::New("quit"));
				break;
			case SDL_MOUSEBUTTONDOWN:
				s->Set(v8::String::New("RTSC_type"), v8::String::New("mouse-down"));
				s->Set(v8::String::New("RTSC_button"), v8::Integer::New(ev.button.button));
				break;
			case SDL_MOUSEBUTTONUP:
				s->Set(v8::String::New("RTSC_type"), v8::String::New("mouse-up"));
				s->Set(v8::String::New("RTSC_button"), v8::Integer::New(ev.button.button));
				break;
			case SDL_MOUSEMOTION:
				s->Set(v8::String::New("RTSC_type"), v8::String::New("mouse-move"));
				s->Set(v8::String::New("RTSC_x"), v8::Integer::New(ev.motion.x));
				s->Set(v8::String::New("RTSC_y"), v8::Integer::New(ev.motion.y));
				break;
			case SDL_KEYDOWN:
				s->Set(v8::String::New("RTSC_type"), v8::String::New("key-down"));
				s->Set(v8::String::New("RTSC_key"), v8::String::New(key_translate(ev.key.keysym.sym)));
				break;
			case SDL_KEYUP:
				s->Set(v8::String::New("RTSC_type"), v8::String::New("key-up"));
				s->Set(v8::String::New("RTSC_key"), v8::String::New(key_translate(ev.key.keysym.sym)));
				break;
			default:
				return v8::Integer::New(0);
		}
		return s;
	}
	return v8::Integer::New(0);
}

v8::Handle<v8::Value> opengl_load_image_from_fs_data(const v8::Arguments& x) {
	v8::HandleScope handle_scope;

	GLuint texture;

	v8::Handle<v8::Object> tex = x[0]->ToObject();
	if (not tex->Has(v8::String::New("RTSC_pointer"))) {
		cerr << "Attempted opengl.load_image_from_fs_data() on something that isn't a data object." << endl;
		return v8::Integer::New(0);
	}
	char* data = (char*) v8::External::Unwrap(tex->Get(v8::String::New("RTSC_pointer")));

	// Note that 0x58455403 == "\x03TEX", the texture magic number.
	int magic_number = *(int*)data; data += 4;
	if (magic_number != 0x58455403) {
		cerr << "Loaded texture string from \"" << *v8::String::AsciiValue(tex->Get(v8::String::New("RTSC_source"))) << "\" isn't of the correct format." << endl;
		cerr << "Did you forget a texture:: specifier in your project file?" << endl;
		return v8::Integer::New(0);
	}
	int width = *(int*)data; data += 4;
	int height = *(int*)data; data += 4;
	int bpp = *(unsigned char*)data; data += 1;
	data += 3;

	// Standard OpenGL texture creation code
	glPixelStorei(GL_UNPACK_ALIGNMENT, 4);

	glGenTextures(1, &texture);
	glBindTexture(GL_TEXTURE_2D, texture);

	//glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,minFilter);
	//glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,magFilter);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR_MIPMAP_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_NEAREST);

	if (bpp == 3) {
		gluBuild2DMipmaps(GL_TEXTURE_2D, 3, width, height, GL_BGR, GL_UNSIGNED_BYTE, data);
	} else {
		gluBuild2DMipmaps(GL_TEXTURE_2D, 4, width, height, GL_BGRA, GL_UNSIGNED_BYTE, data);
	}

	v8::Handle<v8::Object> s = v8::Object::New();
	s->Set(v8::String::New("RTSC_texture_num"), v8::Integer::New(texture));
	s->Set(v8::String::New("RTSC_width"), v8::Integer::New(width));
	s->Set(v8::String::New("RTSC_height"), v8::Integer::New(height));

	return handle_scope.Close(s);
}

v8::Handle<v8::Value> opengl_load_image_from_file(const v8::Arguments& x) {
	v8::HandleScope handle_scope;

	GLuint texture;
	SDL_Surface* bmpFile;

	v8::String::AsciiValue pathstr(x[0]);
	const char* path = *pathstr;

	// Load the bitmap
	bmpFile = SDL_LoadBMP(path);

	if (bmpFile == NULL) {
		cerr << "Failed to load texture: " << path << endl;
		return v8::Integer::New(0);
	}

	// Standard OpenGL texture creation code
	glPixelStorei(GL_UNPACK_ALIGNMENT, 4);

	glGenTextures(1, &texture);
	glBindTexture(GL_TEXTURE_2D, texture);

	//glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,minFilter);
	//glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,magFilter);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR_MIPMAP_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_NEAREST);

	gluBuild2DMipmaps(GL_TEXTURE_2D, 3, bmpFile->w, bmpFile->h, GL_BGR, GL_UNSIGNED_BYTE, bmpFile->pixels);

	v8::Handle<v8::Object> s = v8::Object::New();
	s->Set(v8::String::New("RTSC_texture_num"), v8::Integer::New(texture));
	s->Set(v8::String::New("RTSC_width"), v8::Integer::New(bmpFile->w));
	s->Set(v8::String::New("RTSC_height"), v8::Integer::New(bmpFile->h));

	// Free the surface after using it
	SDL_FreeSurface(bmpFile);

	return handle_scope.Close(s);
}

v8::Handle<v8::Value> opengl_begin_frame(const v8::Arguments& x) {
	if(SDL_MUSTLOCK(screen) && SDL_LockSurface(screen) < 0)
		return v8::Integer::New(1);

	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

	glDisable(GL_DEPTH_TEST);
//	glDisable(GL_TEXTURE_2D);
	glDisable(GL_LIGHTING);
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glOrtho(0, screen_width, screen_height, 0, 0, 1);
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();

	return v8::Integer::New(0);
}

v8::Handle<v8::Value> opengl_end_frame(const v8::Arguments& x) {
	SDL_GL_SwapBuffers();

	if (SDL_MUSTLOCK(screen))
		SDL_UnlockSurface(screen);

	SDL_Flip(screen);
	return v8::Integer::New(0);
}

v8::Handle<v8::Value> opengl_draw_texture(const v8::Arguments& args) {
	v8::Handle<v8::Object> tex = args[0]->ToObject();
	double x = args[1]->NumberValue();
	double y = args[2]->NumberValue();
	// Make sure the texture num is set.
	if (not tex->Has(v8::String::New("RTSC_texture_num"))) {
		cerr << "Attempted to draw invalid texture." << endl;
		return v8::Integer::New(0);
	}
	int texture = tex->Get(v8::String::New("RTSC_texture_num"))->Int32Value();
	int width = tex->Get(v8::String::New("RTSC_width"))->Int32Value();
	int height = tex->Get(v8::String::New("RTSC_height"))->Int32Value();
	glBindTexture(GL_TEXTURE_2D, texture);
	glBegin(GL_QUADS);
	glTexCoord2f(0, 0);
	glVertex2f(x, y);
	glTexCoord2f(0, 1);
	glVertex2f(x, y+height);
	glTexCoord2f(1, 1);
	glVertex2f(x+width, y+height);
	glTexCoord2f(1, 0);
	glVertex2f(x+width, y);
	glEnd();

	return v8::Integer::New(0);
}

v8::Handle<v8::Value> opengl_set_window_title(const v8::Arguments& args) {
	char *title, *icon;
	SDL_WM_GetCaption(&title, &icon);
	v8::String::AsciiValue new_title(args[0]);
	SDL_WM_SetCaption(*new_title, icon);
	return v8::Integer::New(0);
}

v8::Handle<v8::Value> opengl_set_taskbar_name(const v8::Arguments& args) {
	char *title, *icon;
	SDL_WM_GetCaption(&title, &icon);
	v8::String::AsciiValue new_icon(args[0]);
	SDL_WM_SetCaption(title, *new_icon);
	return v8::Integer::New(0);
}

void opengl_init(v8::Handle<v8::Object>& global) {
	//SCOPE(opengl);
	//SET(global, opengl, opengl);
	FUNC(global, launch, opengl_launch);
	FUNC(global, option, opengl_option);
	FUNC(global, quit, opengl_quit);
	FUNC(global, poll, opengl_poll);
	FUNC(global, load_image_from_file, opengl_load_image_from_file);
	FUNC(global, load_image_from_fs_data, opengl_load_image_from_fs_data);
	FUNC(global, begin_frame, opengl_begin_frame);
	FUNC(global, end_frame, opengl_end_frame);
	FUNC(global, draw_texture, opengl_draw_texture);
	FUNC(global, set_window_title, opengl_set_window_title);
	FUNC(global, set_taskbar_name, opengl_set_taskbar_name);
}

