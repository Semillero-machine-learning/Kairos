import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ColdStartBannerComponent } from './core/layout/cold-start-banner.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ColdStartBannerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {}
